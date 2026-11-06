#!/bin/sh

# Configuration
BASE_URL="${BASE_URL:-http://healthdata-local.com:8092/healthData}"
API_KEY="${API_KEY:-c0107b96-78a1-408e-b05f-a65eb3a3d0a8}"
APPLICATION_ID="${APPLICATION_ID:-6ae868c29c434053df8538f7}"
CATALOG_ID="${CATALOG_ID:-550e8400-e29b-41d4-a716-446655440001}"
DATASET_ID="${DATASET_ID:-cbf99905-e17b-4c06-b8d3-a155cf6a6a0c}"

#Catalog status progression: SENT → SUBMITTED → PROCESSING → DECISION_ISSUED
STATUS_TRANSITIONS="PROCESSING DECISION_ISSUED"

STEP=0

for NEW_STATUS in $STATUS_TRANSITIONS; do
 STEP=$((STEP + 1))
 echo "=== Step $STEP: $NEW_STATUS ==="

 curl -s -X PUT "${BASE_URL}/dispatcher/update/status" \
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

#Step 4: Set issue a positive decision

curl -X PUT "${BASE_URL}/dispatcher/decision" \
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
          \"decision_reason\": \"Decision from NCP\"
        }
      ]
    }
  }" | jq .

echo ""
echo "=== Done ==="
