#!/bin/sh
# Replace the build-time API URL placeholder with the runtime value.
# This allows a single image to work in any environment by setting
# NEXT_PUBLIC_API_URL as a runtime env var in docker-compose.

PLACEHOLDER="__NEXT_PUBLIC_API_URL_PLACEHOLDER__"
RUNTIME_URL="${NEXT_PUBLIC_API_URL:-http://localhost:18080/api/v1}"

if [ "$RUNTIME_URL" != "$PLACEHOLDER" ]; then
  echo "Injecting API URL: $RUNTIME_URL"
  find /app/.next /app/server.js -type f \( -name '*.js' -o -name '*.json' \) \
    -exec sed -i "s|$PLACEHOLDER|$RUNTIME_URL|g" {} + 2>/dev/null || true
fi

exec node server.js
