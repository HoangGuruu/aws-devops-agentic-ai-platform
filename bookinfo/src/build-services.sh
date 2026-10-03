#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${BOOKINFO_HUB:?Set registry/repository prefix}"
: "${BOOKINFO_TAG:?Set immutable release tag}"
for service in productpage details ratings reviews; do
  docker build -t "$BOOKINFO_HUB/$service:$BOOKINFO_TAG" "$service"
  if [[ "${1:-}" == "--push" ]]; then docker push "$BOOKINFO_HUB/$service:$BOOKINFO_TAG"; fi
done
