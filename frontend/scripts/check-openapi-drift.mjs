import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const snapshotPath = path.resolve(root, 'contracts/openapi.snapshot.json');
const currentPath = path.resolve(root, 'contracts/openapi.current.json');

function loadJson(file) {
  if (!fs.existsSync(file)) {
    throw new Error(`Missing required file: ${file}`);
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function schemaType(schema = {}) {
  if (schema.$ref) return `ref:${schema.$ref}`;
  if (Array.isArray(schema.anyOf)) return `anyOf:${schema.anyOf.map(schemaType).sort().join('|')}`;
  if (Array.isArray(schema.oneOf)) return `oneOf:${schema.oneOf.map(schemaType).sort().join('|')}`;
  if (schema.type === 'array') return `array<${schemaType(schema.items || {})}>`;
  if (schema.type === 'object') return 'object';
  if (Array.isArray(schema.type)) return schema.type.sort().join('|');
  return schema.type || 'unknown';
}

function normalizeComponents(spec) {
  const components = spec?.components?.schemas ?? {};
  const normalized = {};

  for (const [schemaName, schema] of Object.entries(components)) {
    const props = schema.properties ?? {};
    const required = new Set(schema.required ?? []);
    normalized[schemaName] = {
      required: [...required].sort(),
      properties: Object.fromEntries(
        Object.entries(props)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([propName, propSchema]) => [
            propName,
            {
              type: schemaType(propSchema),
              enum: Array.isArray(propSchema.enum) ? [...propSchema.enum].sort() : null,
              nullable:
                propSchema.nullable === true ||
                (Array.isArray(propSchema.anyOf) && propSchema.anyOf.some((v) => v?.type === 'null')),
              required: required.has(propName),
            },
          ]),
      ),
    };
  }

  return normalized;
}

function compare(oldMap, newMap) {
  const issues = [];
  const schemaNames = new Set([...Object.keys(oldMap), ...Object.keys(newMap)]);

  for (const schemaName of [...schemaNames].sort()) {
    const oldSchema = oldMap[schemaName];
    const newSchema = newMap[schemaName];

    if (!oldSchema || !newSchema) continue;

    const propNames = new Set([
      ...Object.keys(oldSchema.properties ?? {}),
      ...Object.keys(newSchema.properties ?? {}),
    ]);

    for (const propName of [...propNames].sort()) {
      const oldProp = oldSchema.properties[propName];
      const newProp = newSchema.properties[propName];
      if (!oldProp || !newProp) continue;

      if (oldProp.required !== newProp.required) {
        issues.push(`${schemaName}.${propName}: required flag changed (${oldProp.required} -> ${newProp.required})`);
      }
      if (oldProp.type !== newProp.type) {
        issues.push(`${schemaName}.${propName}: type changed (${oldProp.type} -> ${newProp.type})`);
      }
      if (JSON.stringify(oldProp.enum) !== JSON.stringify(newProp.enum)) {
        const oldSet = new Set(oldProp.enum ?? []);
        const newSet = new Set(newProp.enum ?? []);
        const added = [...newSet].filter((v) => !oldSet.has(v));
        const removed = [...oldSet].filter((v) => !newSet.has(v));
        if (added.length || removed.length) {
          issues.push(`${schemaName}.${propName}: enum changed (added: [${added.join(', ')}], removed: [${removed.join(', ')}])`);
        }
      }
      if (oldProp.nullable !== newProp.nullable) {
        issues.push(`${schemaName}.${propName}: nullable changed (${oldProp.nullable} -> ${newProp.nullable})`);
      }
    }
  }

  return issues;
}

function additionalGuards(spec) {
  const guards = [];
  const components = spec?.components?.schemas ?? {};

  // Guard pagination metadata omission.
  const paginationSchemas = Object.entries(components).filter(([name]) =>
    name.toLowerCase().includes('paginatedresponse'),
  );
  for (const [name, schema] of paginationSchemas) {
    const required = new Set(schema.required ?? []);
    for (const key of ['items', 'total', 'skip', 'limit', 'has_more']) {
      if (!required.has(key)) {
        guards.push(`${name}: missing required pagination key '${key}'`);
      }
    }
  }

  return guards;
}

const oldSpec = loadJson(snapshotPath);
const newSpec = loadJson(currentPath);

const drift = compare(normalizeComponents(oldSpec), normalizeComponents(newSpec));
const guards = additionalGuards(newSpec);
const failures = [...drift, ...guards];

if (failures.length > 0) {
  console.error('OpenAPI compatibility check failed:\n');
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log('OpenAPI compatibility check passed.');
