#!/usr/bin/env bash

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
MONGO_CONTAINER="mongos_router"
DB_NAME="readersDb"
DATA_DIR="$ROOT_DIR/db-generation"
LOADERS_DIR="$ROOT_DIR/shard_loaders"
TMP_DIR="/tmp/mdb_seed"

mongo_js() {
  local script_path="$1"
  docker exec -i "$MONGO_CONTAINER" mongosh --quiet < "$script_path"
}

mongo_import() {
  local source_file="$1"
  local target_collection="$2"
  docker exec -i "$MONGO_CONTAINER" mongoimport --db "$DB_NAME" --collection "$target_collection" --file "$TMP_DIR/$source_file"
}

mongo_export_import() {
  local source_collection="$1"
  local target_collection="$2"
  local export_path="$TMP_DIR/${source_collection}.json"
  docker exec -i "$MONGO_CONTAINER" mongoexport --db "$DB_NAME" --collection "$source_collection" --out "$export_path"
  docker exec -i "$MONGO_CONTAINER" mongoimport --db "$DB_NAME" --collection "$target_collection" --file "$export_path"
}

prepare_container_files() {
  docker exec "$MONGO_CONTAINER" mkdir -p "$TMP_DIR"
  docker cp "$DATA_DIR/user.dat" "$MONGO_CONTAINER":"$TMP_DIR/user.dat"
  docker cp "$DATA_DIR/article.dat" "$MONGO_CONTAINER":"$TMP_DIR/article.dat"
  docker cp "$DATA_DIR/read.dat" "$MONGO_CONTAINER":"$TMP_DIR/read.dat"
}

echo "Preparing seed files in container..."
prepare_container_files

echo "Configuring sharding for base collections..."
mongo_js "$LOADERS_DIR/configure_users_sharding.js"
mongo_js "$LOADERS_DIR/configure_articles_sharding.js"

echo "Importing base data..."
mongo_import "user.dat" "users"
mongo_import "article.dat" "articles"

mongo_js "$LOADERS_DIR/build_science_articles.js"
mongo_js "$LOADERS_DIR/configure_science_articles_sharding.js"

echo "Importing reads into staging collection..."
mongo_import "read.dat" "reads_unsharded"

echo "Building derived collections..."
mongo_js "$LOADERS_DIR/build_reads_unsharded.js"
mongo_js "$LOADERS_DIR/build_bereads_unsharded.js"
mongo_js "$LOADERS_DIR/build_pop_ranks_unsharded.js"
mongo_js "$LOADERS_DIR/build_science_bereads.js"

echo "Configuring sharding for derived collections..."
mongo_js "$LOADERS_DIR/configure_reads_sharding.js"
mongo_js "$LOADERS_DIR/configure_bereads_sharding.js"
mongo_js "$LOADERS_DIR/configure_pop_ranks_sharding.js"
mongo_js "$LOADERS_DIR/configure_science_bereads_sharding.js"

echo "Loading derived collections into sharded targets..."
mongo_export_import "reads_unsharded" "reads"
mongo_export_import "bereads_unsharded" "bereads"
mongo_export_import "pop_ranks_unsharded" "pop_ranks"

mongo_js "$LOADERS_DIR/configure_science_bereads_sharding.js"

echo "Cleaning temporary collections..."
mongo_js "$LOADERS_DIR/drop_temp_collections.js"

echo "Data load complete."
