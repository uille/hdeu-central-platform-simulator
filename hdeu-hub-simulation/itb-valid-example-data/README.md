
# Upload catalog

curl -X PUT "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001" -H "Content-Type: text/turtle" -H "X-API-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b" --data-binary @./example_catalog.ttl

# Optional check catalog now exists

curl "http://healthdata-local.com:8092/hub/api/repo/catalogues?valueType=metadata" -H "X-Api-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b"

# Upload the data set into the catalog

curl -X POST "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001/datasets" -H "Content-Type: text/turtle" -H "X-API-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b" --data-binary @./example_dataset.ttl

# Optional check dataset now exists

curl -v "http://healthdata-local.com:8092/hub/api/repo/catalogues/550e8400-e29b-41d4-a716-446655440001/datasets?valueType=metadata" -H "X-Api-Key: 7c6a7c98-20e1-4915-ba0c-985b6724560b"

# just some development spells don't mind these

mongosh 'mongodb://mongoAdmin:mongoSecret123!@localhost:27017/healthData-DataAccessDB?authSource=admin'

mongosh 'mongodb://mongoAdmin:mongoSecret123!@localhost:27017/healthData-DataAccessDB?authSource=admin' --eval 'db.DATA_ACCESS_APPLICATION.find({userId:"local_user"})'

USER_ID="local_user" mongosh 'mongodb://mongoAdmin:mongoSecret123!@localhost:27017/healthData-DataAccessDB?authSource=admin' --eval 'const user_id = process.env.USER_ID;JSON.stringify(db.DATA_ACCESS_APPLICATION.aggregate([ {$match: {userId: user_id}}, {$project: {userId:1,datasets:{dataset_id:1,catalog_id:1,decisions:1},catalogs:1}}, {$addFields: {application_id: "$_id"}},{$project: {_id:0,application_id:1, userId:1,catalogs:1,datasets:1}}]).toArray())'|jq