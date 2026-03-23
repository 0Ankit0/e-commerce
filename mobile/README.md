# Mobile Runtime Guide

The mobile app is a Flutter client for the same FastAPI auth and commerce APIs used by the web app. Social auth provider visibility comes from `/auth/social/providers/`, and browser-style providers continue through the existing WebView flow in this deployable-core pass.

## Local Development

- `flutter pub get`
- `flutter run`
- Configure `BASE_URL` in `mobile/.env` for the backend `api/v1` base URL.

## Verification

- `flutter analyze`
- `flutter test`

## Key Runtime Areas

- Auth flows under `lib/features/auth`
- Commerce flows under `lib/features/commerce`
- Shared routing in `lib/core/router/app_router.dart`
- Network endpoint constants in `lib/core/network/api_endpoints.dart`
