#!/usr/bin/env bash

HOSTIP=$(hostname -I | awk '{print $1}')
export HOSTIP

stop_all_containers() {
  docker stop $(docker ps -aq)
}

remove_all_containers() {
  docker rm $(docker ps -aq)
}

init_config_rs() {
  docker exec -it config1 mongosh --eval "rs.initiate({
    _id: 'configReplSet',
    configsvr: true,
    members: [
      { _id: 0, host: '${HOSTIP}:27019' },
      { _id: 1, host: '${HOSTIP}:27020' },
      { _id: 2, host: '${HOSTIP}:27021' }
    ]
  })"
}

init_shard_rs() {
  local repl_set="$1"
  local primary_port="$2"
  local secondary_port="$3"
  local primary_container="$4"

  docker exec -it "$primary_container" mongosh --eval "rs.initiate({
    _id: '${repl_set}',
    members: [
      { _id: 0, host: '${HOSTIP}:${primary_port}' },
      { _id: 1, host: '${HOSTIP}:${secondary_port}' }
    ]
  })"
}

add_shards() {
  docker exec -it mongos_router mongosh --eval "sh.addShard('shard1ReplSet/${HOSTIP}:27031,${HOSTIP}:27032')"
  docker exec -it mongos_router mongosh --eval "sh.addShard('shard2ReplSet/${HOSTIP}:27033,${HOSTIP}:27034')"
}

reset_data_dirs() {
  sudo rm -rf data
  mkdir -p data/config1 data/config2 data/config3
  mkdir -p data/shard1_replica1 data/shard1_replica2
  mkdir -p data/shard2_replica1 data/shard2_replica2
}

echo "Stopping existing containers..."
stop_all_containers
remove_all_containers

echo "Resetting MongoDB data directories..."
reset_data_dirs

echo "Starting MongoDB containers..."
docker compose -f mongodb/docker-compose.yml up -d

echo "Waiting for containers to initialize..."
sleep 10

echo "Initializing config replica set..."
init_config_rs

echo "Initializing shard replica sets..."
init_shard_rs "shard1ReplSet" "27031" "27032" "shard1_replica1"
init_shard_rs "shard2ReplSet" "27033" "27034" "shard2_replica1"

echo "Waiting for replica sets to stabilize..."
sleep 20

echo "Adding shards to cluster..."
add_shards

echo "MongoDB sharded cluster is ready."

docker run -d -p 6379:6379 redis/redis-stack:latest

docker run -d -p 27051:27017 mongo:latest
