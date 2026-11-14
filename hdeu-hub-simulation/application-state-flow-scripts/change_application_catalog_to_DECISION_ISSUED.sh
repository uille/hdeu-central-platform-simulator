#!/bin/sh

# Configuration
BASE_URL="${BASE_URL:-https://healthdata-local.com:8092/healthData}"
API_KEY="${API_KEY:-c0107b96-78a1-408e-b05f-a65eb3a3d0a8}"
APPLICATION_ID="${APPLICATION_ID}"
CATALOG_ID="${CATALOG_ID}"

# Validate required environment variables
if [ -z "$APPLICATION_ID" ]; then
  echo "ERROR: APPLICATION_ID environment variable is not set." >&2
  exit 1
fi

if [ -z "$CATALOG_ID" ]; then
  echo "ERROR: CATALOG_ID environment variable is not set." >&2
  exit 1
fi

#Catalog status progression: SENT → SUBMITTED → PROCESSING → DECISION_ISSUED
STATUS_TRANSITIONS="PROCESSING DECISION_ISSUED"

STEP=0

for NEW_STATUS in $STATUS_TRANSITIONS; do
 STEP=$((STEP + 1))
 echo "=== Step $STEP: $NEW_STATUS ==="

 curl -k -s -X PUT "${BASE_URL}/dispatcher/update/status" \
   -H "Content-Type: application/json" \
   -H "X-API-Key: ${API_KEY}" \
   -d "{
     \"type\": \"application\",
     \"operation\": \"catalog_status\",
     \"objectId\": \"${APPLICATION_ID}\",
     \"payload\": {
       \"application_type\": \"DATA_ACCESS_APPLICATION\",
       \"status\": \"${NEW_STATUS}\",
       \"catalog_id\": \"${CATALOG_ID}\",
       \"statusPayload\": {}
     }
   }" | jq .

 if [ $? -ne 0 ]; then
   echo "ERROR: Step $STEP ($NEW_STATUS) failed."
   exit 1
 fi
 echo ""
done

echo ""
echo "=== Done ==="
