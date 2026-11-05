
# Upload catalog

curl -X PUT "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001" -H "Content-Type: text/turtle" -H "X-API-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b" --data-binary @./example_catalog.ttl

# Optional check catalog now exists

curl "http://healthdata-local.com:8092/hub/api/repo/catalogues?valueType=metadata" -H "X-Api-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b"

# Upload the data set into the catalog

curl -X POST "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001/datasets" -H "Content-Type: text/turtle" -H "X-API-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b" --data-binary @./example_dataset.ttl

# Optional check dataset now exists

curl -v "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001/datasets?valueType=metadata" -H "X-Api-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b"


# When application has been submitted and at ON-GOING state, change the catalog status and dataset specific permit

by running change_to_permit_granted_state.sh

