#!/bin/bash
echo "Copying data to Mongos Router container...."
docker cp db-generation/user.dat mongos_router:/user.dat
docker cp db-generation/article.dat mongos_router:/article.dat
docker cp db-generation/read.dat mongos_router:/read.dat
docker cp shard_loaders mongos_router:/shard_loaders

echo "Loading shards with user data...."
docker exec -it mongos_router bash -c "mongosh < shard_loaders/users_loader.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/articles_loader.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/sci_articles_shard_configurer.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/reads_shard_configurer.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/bereads_shard_configurer.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/sci_bereads_shard_configurer.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/sci_bereads_shard_configurer.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/pop_rank_shard_configurer.js"

echo "Waiting for shards to stabilize..."
sleep 10
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection users --file user.dat"
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection articles --file article.dat"
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection reads_unsharded --file read.dat"

sleep 5

docker exec -it mongos_router bash -c "mongosh < shard_loaders/sci_articles_loader.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/reads_loader.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/bereads_loader.js"
docker exec -it mongos_router bash -c "mongosh < shard_loaders/pop_rank_loader.js"

sleep 5

docker exec -it mongos_router bash -c "mongoexport --db readersDb --collection reads_unsharded --out reads_full.json"
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection reads --file reads_full.json"

docker exec -it mongos_router bash -c "mongoexport --db readersDb --collection bereads_unsharded --out bereads_full.json"
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection bereads --file bereads_full.json"
sleep 5

docker exec -it mongos_router bash -c "mongosh < shard_loaders/sci_bereads_loader.js"

docker exec -it mongos_router bash -c "mongoexport --db readersDb --collection pop_ranks_unsharded --out pop_ranks_full.json"
docker exec -it mongos_router bash -c "mongoimport --db readersDb --collection pop_ranks --file pop_ranks_full.json"

sleep 5

docker exec -it mongos_router bash -c "mongosh < shard_loaders/drop_tmp_dbs.js"

echo "Data loaded into MongoDb collections...."