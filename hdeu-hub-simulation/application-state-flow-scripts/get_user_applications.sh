#!/bin/bash

# Check if USER_ID is provided
if [ $# -lt 1 ]; then
  echo "Usage: $0 <USER_ID>"
  exit 1
fi

USER_ID="$1"

echo "Fetching data for USER_ID: $USER_ID"

# Run the mongosh query and extract variables
JSON_DATA=$(mongosh 'mongodb://mongoAdmin:mongoSecret123!@localhost:27017/healthData-DataAccessDB?authSource=admin' \
  --eval "
    const user_id = '$USER_ID';
    JSON.stringify(db.DATA_ACCESS_APPLICATION.aggregate([
      { \$match: { userId: user_id } },
      { \$project: {
          userId: 1,
          datasets: { dataset_id: 1, catalog_id: 1, decisions: 1 },
          catalogs: 1
        }
      },
      { \$addFields: { application_id: '\$_id' } },
      { \$project: {
          _id: 0,
          application_id: 1,
          userId: 1,
          catalogs: 1,
          datasets: 1
        }
      }
    ]).toArray())
  " 2>/dev/null | jq)

echo "$JSON_DATA"