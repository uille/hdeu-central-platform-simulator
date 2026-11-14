#!/bin/sh

# Configuration
BASE_URL="${BASE_URL:-https://healthdata-local.com:8092/healthData}"
API_KEY="${API_KEY:-c0107b96-78a1-408e-b05f-a65eb3a3d0a8}"
APPLICATION_ID="${APPLICATION_ID}"
CATALOG_ID="${CATALOG_ID}"
DATASET_ID="${DATASET_ID}"
DECISION_REASON="${DECISION_REASON}"

# Validate required environment variables
if [ -z "$APPLICATION_ID" ]; then
  echo "ERROR: APPLICATION_ID environment variable is not set." >&2
  exit 1
fi

if [ -z "$CATALOG_ID" ]; then
  echo "ERROR: CATALOG_ID environment variable is not set." >&2
  exit 1
fi

if [ -z "$DATASET_ID" ]; then
  echo "ERROR: DATASET_ID environment variable is not set." >&2
  exit 1
fi

if [ -z "$DECISION_REASON" ]; then
  echo "ERROR: DECISION_REASON environment variable is not set." >&2
  exit 1
fi

#Issue a positive decision

curl -k -X PUT "${BASE_URL}/dispatcher/decision" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: ${API_KEY}" \
  -d "{
    \"type\": \"application\",
    \"operation\": \"decision\",
    \"objectId\": \"${APPLICATION_ID}\",
    \"payload\": {
      \"application_type\": \"DATA_ACCESS_APPLICATION\",
      \"status\": \"COMPLETED\",
      \"catalog_id\": \"${CATALOG_ID}\",
      \"decisions\": [
        {
          \"dataset_id\": \"${DATASET_ID}\",
          \"decision\": \"POSITIVE_DECISION_ISSUED\",
          \"decision_reason\": \"${DECISION_REASON}\"
        }
      ]
    }
  }" | jq .

echo ""
echo "=== Done ==="
