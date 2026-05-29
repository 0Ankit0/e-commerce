# Project Documentation

This repository keeps `docs/system-design/*` as the canonical design tree for deployable-core documentation. Runtime and operational setup details live alongside each app so the docs gate reflects the code that actually ships.

## Canonical Structure

- [System design index](./system-design/README.md)
- [Requirements](./system-design/requirements/)
- [Analysis](./system-design/analysis/)
- [High-level design](./system-design/high-level-design/)
- [Detailed design](./system-design/detailed-design/)
- [Infrastructure](./system-design/infrastructure/)
- [Implementation status](./system-design/implementation/)

## Runtime Guides

- [Backend runtime docs](../backend/README.md)
- [Frontend runtime docs](../frontend/README.md)
- [Mobile runtime docs](../mobile/README.md)
- [Role-based user manual](./user-manual/README.md)

## Validation

- `python3 scripts/validate_documentation.py`
- `make docs`
- Keep this file and [the system-design index](./system-design/README.md) aligned when the canonical structure changes.
