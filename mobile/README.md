# Mobile Runtime Guide

The mobile app is a Flutter client for the same FastAPI auth and commerce APIs used by the web app. Social auth provider visibility comes from `/auth/social/providers/`, and browser-style providers continue through the existing WebView flow in this deployable-core pass.

## Local Development

- `flutter pub get`
- `flutter run`
- Configure `BASE_URL` in `mobile/.env` for the backend `api/v1` base URL.

## Verification

- `flutter analyze`
- `flutter test`
- Linux desktop build (local/CI):
  - `flutter config --enable-linux-desktop`
  - Install toolchain/system packages required by Flutter Linux embedding
    (`cmake`, `ninja-build`, `pkg-config`, `libgtk-3-dev`, `libstdc++-12-dev`
    or equivalent for your distro).
  - `flutter build linux --debug` (or `--release` in CI for production artifacts).
  - Keep `mobile/linux/flutter/ephemeral/` generated-only; regenerate it via
    Flutter commands rather than committing manual edits.

## Desktop CMake Conventions

- `mobile/linux/flutter/CMakeLists.txt` and
  `mobile/windows/flutter/CMakeLists.txt` both keep the stable, hand-maintained
  Flutter wiring in source control.
- Generated files stay under each platform's `flutter/ephemeral` directory and
  are consumed via `generated_config.cmake`.
- The `flutter_assemble` target is intentionally driven through a symbolic
  `_phony_` output to ensure Flutter backend steps rerun when inputs change.
- Plugin/generated wiring remains isolated in platform-root CMake files via
  `include(flutter/generated_plugins.cmake)` so hand-maintained project logic
  and Flutter-managed plugin glue stay separated.

## Manual Steps After CMake Edits

- No additional manual migration is required.
- If Flutter-generated files are stale, regenerate them with a platform build:
  - Linux: `flutter build linux --debug`
  - Windows: `flutter build windows --debug`
- Do not hand-edit files under `mobile/*/flutter/ephemeral`; treat them as
  generated outputs.
## Key Runtime Areas

- Auth flows under `lib/features/auth`
- Commerce flows under `lib/features/commerce`
- Shared routing in `lib/core/router/app_router.dart`
- Network endpoint constants in `lib/core/network/api_endpoints.dart`
