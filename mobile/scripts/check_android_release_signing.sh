#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_DIR="$ROOT_DIR/android"

if [[ "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: check_android_release_signing.sh [--strict]

Checks Android release signing configuration from either:
1) android/key.properties or android/release-signing.properties, or
2) ANDROID_KEYSTORE_PATH, ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD

By default, missing values produce a warning and exit 0.
Use --strict to fail with exit 1 when config is incomplete.
USAGE
  exit 0
fi

strict_mode=false
if [[ "${1:-}" == "--strict" ]]; then
  strict_mode=true
fi

properties_file=""
for candidate in "$ANDROID_DIR/key.properties" "$ANDROID_DIR/release-signing.properties"; do
  if [[ -f "$candidate" ]]; then
    properties_file="$candidate"
    break
  fi
done

store_file="${ANDROID_KEYSTORE_PATH:-}"
store_password="${ANDROID_KEYSTORE_PASSWORD:-}"
key_alias="${ANDROID_KEY_ALIAS:-}"
key_password="${ANDROID_KEY_PASSWORD:-}"

if [[ -n "$properties_file" ]]; then
  while IFS='=' read -r raw_key raw_value; do
    key="${raw_key//[[:space:]]/}"
    value="${raw_value#${raw_value%%[![:space:]]*}}"
    [[ -z "$key" || "$key" == \#* ]] && continue

    case "$key" in
      storeFile) store_file="${store_file:-$value}" ;;
      storePassword) store_password="${store_password:-$value}" ;;
      keyAlias) key_alias="${key_alias:-$value}" ;;
      keyPassword) key_password="${key_password:-$value}" ;;
    esac
  done < "$properties_file"
fi

missing=()
[[ -z "$store_file" ]] && missing+=("storeFile / ANDROID_KEYSTORE_PATH")
[[ -z "$store_password" ]] && missing+=("storePassword / ANDROID_KEYSTORE_PASSWORD")
[[ -z "$key_alias" ]] && missing+=("keyAlias / ANDROID_KEY_ALIAS")
[[ -z "$key_password" ]] && missing+=("keyPassword / ANDROID_KEY_PASSWORD")

if [[ ${#missing[@]} -gt 0 ]]; then
  message="Android release signing configuration is incomplete. Missing: ${missing[*]}"
  if [[ "$strict_mode" == true ]]; then
    echo "ERROR: $message" >&2
    exit 1
  fi

  echo "WARN: $message"
  exit 0
fi

if [[ "$store_file" != /* ]]; then
  store_file="$ANDROID_DIR/$store_file"
fi

if [[ ! -f "$store_file" ]]; then
  message="Android keystore file does not exist at path: $store_file"
  if [[ "$strict_mode" == true ]]; then
    echo "ERROR: $message" >&2
    exit 1
  fi

  echo "WARN: $message"
  exit 0
fi

if command -v keytool >/dev/null 2>&1; then
  if ! keytool -list -keystore "$store_file" -storepass "$store_password" -alias "$key_alias" >/dev/null 2>&1; then
    message="Unable to verify keystore/alias credentials with keytool. Check store password and alias."
    if [[ "$strict_mode" == true ]]; then
      echo "ERROR: $message" >&2
      exit 1
    fi

    echo "WARN: $message"
    exit 0
  fi
else
  echo "WARN: keytool not found; skipping keystore/alias verification."
fi

echo "Android release signing configuration is complete."
