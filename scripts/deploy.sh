#!/bin/bash
set -euo pipefail

echo "=== Building SAM application ==="
sam build --no-cached

echo ""
echo "=== Deploying SAM application ==="
if [ "${1:-}" = "--guided" ]; then
    sam deploy --guided
else
    sam deploy --no-confirm-changeset
fi

echo ""
echo "=== Deployment complete ==="
sam list stack-outputs --stack-name imagekit-mcp-server --output json 2>/dev/null || true
