#!/bin/bash


HOSTIP=$(hostname -I | awk '{print $1}') 

# Export HOSTIP to make it available for docker-compose
export HOSTIP

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
sudo rm -rf data


# Create directories for data storage
echo "Creating directories for MongoDB data..."
mkdir -p data/config1
mkdir -p data/config2
mkdir -p data/config3
mkdir -p data/shard1_replica1
mkdir -p data/shard1_replica2
mkdir -p data/shard2_replica1
mkdir -p data/shard2_replica2


# Start all containers
echo "Starting MongoDB containers..."
cd mongodb
docker compose up -d

# Wait for the containers to initialize
echo "Waiting for containers to initialize..."
sleep 10

# Initialize Config Replica Set
echo "Initializing Config Replica Set..."
docker exec -it config1 mongosh --eval "rs.initiate({
  _id: 'configReplSet',
  configsvr: true,
  members: [
    { _id: 0, host: '${HOSTIP}:27019'},
    { _id: 1, host: '${HOSTIP}:27020'},
    { _id: 2, host: '${HOSTIP}:27021'}
  ]
})"

# Initialize Shard 1 Replica Set
echo "Initializing Shard 1 Replica Set..."
docker exec -it shard1_replica1 mongosh --eval "rs.initiate({
  _id: 'shard1ReplSet',
  members: [
    { _id: 0, host: '${HOSTIP}:27031' },
    { _id: 1, host: '${HOSTIP}:27032' }
  ]
})"

# Initialize Shard 2 Replica Set
echo "Initializing Shard 2 Replica Set..."
docker exec -it shard2_replica1 mongosh --eval "rs.initiate({
  _id: 'shard2ReplSet',
  members: [
    { _id: 0, host: '${HOSTIP}:27033' },
    { _id: 1, host: '${HOSTIP}:27034' }
  ]
})"

# Wait for replica sets to stabilize
echo "Waiting for replica sets to stabilize..."
sleep 20

# Add Shards to the Cluster
echo "Adding Shards to the Cluster..."
docker exec -it mongos_router mongosh --eval "sh.addShard('shard1ReplSet/${HOSTIP}:27031,${HOSTIP}:27032')"
docker exec -it mongos_router mongosh --eval "sh.addShard('shard2ReplSet/${HOSTIP}:27033,${HOSTIP}:27034')"


echo "MongoDB Sharded Cluster is successfully set up!"

docker run -d -p 6379:6379 redis/redis-stack:latest

docker run -d -p 27051:27017 mongo:latest