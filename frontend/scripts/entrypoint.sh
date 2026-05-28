#!/bin/sh
# Replace build-time NEXT_PUBLIC_* placeholders with runtime values.
# This allows a single image to work in any environment by setting these
# vars at runtime (e.g. in docker-compose).

API_URL_PLACEHOLDER="__NEXT_PUBLIC_API_URL_PLACEHOLDER__"
API_URL_RUNTIME="${NEXT_PUBLIC_API_URL:-http://localhost:18080/api/v1}"

LEXICAL_WEIGHT_PLACEHOLDER="__NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT_PLACEHOLDER__"
LEXICAL_WEIGHT_RUNTIME="${NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT:-0.5}"

if [ "$API_URL_RUNTIME" != "$API_URL_PLACEHOLDER" ]; then
  echo "Injecting API URL: $API_URL_RUNTIME"
  find /app/.next /app/server.js -type f \( -name '*.js' -o -name '*.json' \) \
    -exec sed -i "s|$API_URL_PLACEHOLDER|$API_URL_RUNTIME|g" {} + 2>/dev/null || true
fi

if [ "$LEXICAL_WEIGHT_RUNTIME" != "$LEXICAL_WEIGHT_PLACEHOLDER" ]; then
  echo "Injecting default lexical weight: $LEXICAL_WEIGHT_RUNTIME"
  find /app/.next /app/server.js -type f \( -name '*.js' -o -name '*.json' \) \
    -exec sed -i "s|$LEXICAL_WEIGHT_PLACEHOLDER|$LEXICAL_WEIGHT_RUNTIME|g" {} + 2>/dev/null || true
fi

exec node server.js
