'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, ArrowDown, ArrowUp, Plus, Save, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAdminCategoryMutations, useCatalogCategories } from '@/hooks/use-catalog';
import type { CatalogCategory, CategoryAttributeSchema } from '@/types';
import { deriveCategoryLevel, wouldCreateCycle } from '@/lib/category-hierarchy';

type AttributeType = CategoryAttributeSchema['type'];

const EMPTY_ATTRIBUTE: CategoryAttributeSchema = {
  name: '',
  type: 'text',
  required: false,
  options: [],
  description: '',
};

function CategoryForm({
  category,
  categories,
  onSubmit,
  submitLabel,
}: {
  category?: CatalogCategory;
  categories: CatalogCategory[];
  onSubmit: (payload: {
    name: string;
    slug: string;
    parent_id?: string;
    level: number;
    description: string;
    attributes: CategoryAttributeSchema[];
    sort_order: number;
    expected_updated_at?: string;
  }) => void;
  submitLabel: string;
}) {
  const [name, setName] = useState(category?.name ?? '');
  const [slug, setSlug] = useState(category?.slug ?? '');
  const [parentId, setParentId] = useState(category?.parent_id ?? '');
  const [description, setDescription] = useState(category?.description ?? '');
  const [sortOrder, setSortOrder] = useState(String(category?.sort_order ?? 0));
  const [attributes, setAttributes] = useState<CategoryAttributeSchema[]>(category?.attributes ?? []);
  const [error, setError] = useState('');

  const level = useMemo(() => {
    return deriveCategoryLevel(parentId, categories);
  }, [categories, parentId]);

  const potentialParents = categories.filter((item) => item.id !== category?.id && item.level < 3);

  const addAttribute = () => setAttributes((prev) => [...prev, { ...EMPTY_ATTRIBUTE }]);
  const updateAttribute = (index: number, next: Partial<CategoryAttributeSchema>) => {
    setAttributes((prev) => prev.map((item, i) => (i === index ? { ...item, ...next } : item)));
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    if (category?.id && wouldCreateCycle(category.id, parentId, categories)) {
      setError('Cannot move a category inside its own descendants.');
      return;
    }
    if (level > 3) {
      setError('Category depth cannot exceed 3 levels.');
      return;
    }
    const cleanedAttributes = attributes
      .filter((item) => item.name.trim())
      .map((item) => ({
        ...item,
        name: item.name.trim(),
        options: (item.options ?? []).filter(Boolean),
        description: item.description.trim(),
      }));
    onSubmit({
      name: name.trim(),
      slug: slug.trim(),
      parent_id: parentId || undefined,
      level,
      description: description.trim(),
      attributes: cleanedAttributes,
      sort_order: Number(sortOrder || 0),
      expected_updated_at: category?.updated_at,
    });
  };

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid gap-3 md:grid-cols-2">
        <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Category name" required />
        <Input value={slug} onChange={(event) => setSlug(event.target.value)} placeholder="category-slug" required />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <select className="h-10 rounded-md border px-3 text-sm" value={parentId} onChange={(e) => setParentId(e.target.value)}>
          <option value="">No parent (L1)</option>
          {potentialParents.map((item) => (
            <option key={item.id} value={item.id}>{item.name} (L{item.level})</option>
          ))}
        </select>
        <Input value={String(level)} readOnly aria-label="category-level" />
        <Input value={sortOrder} onChange={(event) => setSortOrder(event.target.value)} placeholder="Sort order" type="number" />
      </div>
      <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description" />

      <div className="space-y-2 rounded-lg border p-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold">Attribute schema</p>
          <Button type="button" variant="outline" size="sm" onClick={addAttribute}><Plus className="mr-1 h-3 w-3" /> Add</Button>
        </div>
        {attributes.map((attr, index) => (
          <div key={`${attr.name}-${index}`} className="grid gap-2 md:grid-cols-5">
            <Input value={attr.name} onChange={(e) => updateAttribute(index, { name: e.target.value })} placeholder="attribute name" />
            <Input
              value={attr.description}
              onChange={(e) => updateAttribute(index, { description: e.target.value })}
              placeholder="description"
            />
            <select
              className="h-10 rounded-md border px-3 text-sm"
              value={attr.type}
              onChange={(e) => updateAttribute(index, { type: e.target.value as AttributeType })}
            >
              <option value="text">text</option>
              <option value="number">number</option>
              <option value="boolean">boolean</option>
              <option value="select">select</option>
            </select>
            <Input
              value={(attr.options ?? []).join(',')}
              onChange={(e) => updateAttribute(index, { options: e.target.value.split(',').map((item) => item.trim()) })}
              placeholder="option1,option2"
            />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={attr.required} onChange={(e) => updateAttribute(index, { required: e.target.checked })} />
              Required
            </label>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit"><Save className="mr-2 h-4 w-4" /> {submitLabel}</Button>
    </form>
  );
}

export default function AdminCatalogPage() {
  const { data } = useCatalogCategories();
  const categories = data?.items ?? [];
  const { createCategory, updateCategory, deleteCategory, reorderCategories } = useAdminCategoryMutations();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState('');
  const [globalError, setGlobalError] = useState('');

  const saveCategory = async (payload: {
    name: string;
    slug: string;
    parent_id?: string;
    level: number;
    description: string;
    attributes: CategoryAttributeSchema[];
    sort_order: number;
    expected_updated_at?: string;
  }) => {
    try {
      setGlobalError('');
      if (editingId) {
        await updateCategory.mutateAsync({ id: editingId, payload });
      } else {
        await createCategory.mutateAsync(payload);
      }
      setEditingId(null);
    } catch {
      setGlobalError('Save failed. Check slug uniqueness and stale updates.');
    }
  };

  const move = async (category: CatalogCategory, delta: number) => {
    const siblings = categories
      .filter((item) => item.parent_id === category.parent_id)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    const index = siblings.findIndex((item) => item.id === category.id);
    const target = siblings[index + delta];
    if (!target) return;
    const payload = categories.map((item) => {
      if (item.id === category.id) return { id: item.id, parent_id: item.parent_id, sort_order: target.sort_order ?? 0 };
      if (item.id === target.id) return { id: item.id, parent_id: item.parent_id, sort_order: category.sort_order ?? 0 };
      return { id: item.id, parent_id: item.parent_id, sort_order: item.sort_order ?? 0 };
    });
    await reorderCategories.mutateAsync(payload);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Category management</CardTitle>
          <CardDescription>Create, edit, reorder, merge, and model custom attributes with max depth 3.</CardDescription>
        </CardHeader>
        <CardContent>
          <CategoryForm
            category={categories.find((item) => item.id === editingId)}
            categories={categories}
            submitLabel={editingId ? 'Update category' : 'Create category'}
            onSubmit={saveCategory}
          />
          {globalError && (
            <p className="mt-3 flex items-center gap-2 text-sm text-red-600"><AlertTriangle className="h-4 w-4" /> {globalError}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Hierarchy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {categories
            .sort((a, b) => a.level - b.level || (a.sort_order ?? 0) - (b.sort_order ?? 0))
            .map((category) => (
              <div key={category.id} className="flex flex-wrap items-center gap-2 rounded-md border p-3">
                <p className="min-w-60 text-sm" style={{ marginLeft: `${(category.level - 1) * 16}px` }}>
                  {category.name} <span className="text-xs text-muted-foreground">({category.slug})</span>
                </p>
                <Button variant="outline" size="sm" onClick={() => move(category, -1)}><ArrowUp className="h-3 w-3" /></Button>
                <Button variant="outline" size="sm" onClick={() => move(category, 1)}><ArrowDown className="h-3 w-3" /></Button>
                <Button variant="outline" size="sm" onClick={() => setEditingId(category.id)}>Edit</Button>
                <select className="h-9 rounded-md border px-2 text-xs" value={deleteTargetId} onChange={(e) => setDeleteTargetId(e.target.value)}>
                  <option value="">Delete without migration</option>
                  {categories.filter((item) => item.id !== category.id).map((item) => (
                    <option key={item.id} value={item.id}>Migrate to {item.name}</option>
                  ))}
                </select>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={async () => {
                    try {
                      setGlobalError('');
                      await deleteCategory.mutateAsync({ id: category.id, migrateToCategoryId: deleteTargetId || undefined });
                    } catch {
                      setGlobalError('Delete failed. Descendants require a migration target and hierarchy must remain valid.');
                    }
                  }}
                >
                  <Trash2 className="mr-1 h-3 w-3" /> Delete
                </Button>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}
