#!/bin/bash
set -euo pipefail

HOSTIP=$(hostname -I | awk '{print $1}')
export HOSTIP

echo "Starting shard3 containers..."
mkdir -p data/shard3_replica1 data/shard3_replica2

if [ -n "$(ls -A data/shard3_replica1 2>/dev/null)" ] || [ -n "$(ls -A data/shard3_replica2 2>/dev/null)" ]; then
  if [ "${RESET_SHARD3:-0}" = "1" ]; then
    echo "Resetting shard3 data directories..."
    docker compose -f mongodb/docker-compose.yml stop shard3_replica1 shard3_replica2 >/dev/null 2>&1 || true
    if ! docker run --rm -u 0 -v "$(pwd)/data/shard3_replica1:/data/db" mongo:latest bash -c "rm -rf /data/db/*"; then
      echo "Failed to clear data/shard3_replica1 with docker. Please clear it manually with sudo."
      exit 1
    fi
    if ! docker run --rm -u 0 -v "$(pwd)/data/shard3_replica2:/data/db" mongo:latest bash -c "rm -rf /data/db/*"; then
      echo "Failed to clear data/shard3_replica2 with docker. Please clear it manually with sudo."
      exit 1
    fi
  else
    echo "Shard3 data directories are not empty. Set RESET_SHARD3=1 to wipe them."
    exit 1
  fi
fi

docker compose -f mongodb/docker-compose.yml up -d shard3_replica1 shard3_replica2

echo "Waiting for shard3 mongod to accept connections..."
sleep 8

status=$(docker exec -i shard3_replica1 mongosh --quiet --eval "try { rs.status().ok } catch (e) { 0 }")
if [ "$status" != "1" ]; then
  echo "Initializing shard3 replica set..."
  docker exec -i shard3_replica1 mongosh --eval "rs.initiate({
    _id: 'shard3ReplSet',
    members: [
      { _id: 0, host: '${HOSTIP}:27035' },
      { _id: 1, host: '${HOSTIP}:27036' }
    ]
  })"
fi

echo "Waiting for shard3 primary..."
for i in $(seq 1 20); do
  state=$(docker exec -i shard3_replica1 mongosh --quiet --eval "try { rs.status().myState } catch (e) { 0 }")
  if [ "$state" = "1" ]; then
    break
  fi
  sleep 2
done

echo "Registering shard3 with mongos..."
exists=$(docker exec -i mongos_router mongosh --quiet --eval "db.getSiblingDB('config').shards.findOne({_id: 'shard3ReplSet'}) ? 1 : 0")
if [ "$exists" != "1" ]; then
  docker exec -i mongos_router mongosh --eval "sh.addShard('shard3ReplSet/${HOSTIP}:27035,${HOSTIP}:27036')"
fi

echo "Shard3 added. Current shard list:"
docker exec -i mongos_router mongosh --quiet --eval "sh.status()"
