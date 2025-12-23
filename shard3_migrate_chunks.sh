#!/bin/bash
set -euo pipefail

echo "Moving chunks from shard2 to shard3 (articles + pop_ranks)..."

echo "Pre-cleaning orphans on target shard (shard3ReplSet)..."
docker exec -i shard3_replica1 mongosh --quiet --eval "
    print('Cleaning orphans on Shard3...');
    var nsList = ['readersDb.articles', 'readersDb.pop_ranks'];
    nsList.forEach(ns => {
        var nextKey = { };
        while (nextKey != null) {
            var res = db.adminCommand({ cleanupOrphaned: ns, startingFromKey: nextKey });
            if (res.ok) nextKey = res.stoppedAtKey;
            else nextKey = null;
        }
        print('Cleaned ' + ns);
    });
" || true 

docker exec -i mongos_router mongosh --quiet <<'EOF'
const targetShard = "shard3ReplSet";
const sourceShard = "shard2ReplSet";
const db = db.getSiblingDB("readersDb");
const config = db.getSiblingDB("config");

function addTag(tag) {
  try {
    sh.addShardTag(targetShard, tag);
    print(`Added tag ${tag} to ${targetShard}`);
  } catch (e) {
    print(`Tag ${tag} may already exist: ${e.message}`);
  }
}

function shardMatchesSource(shardName) {
  if (!shardName) {
    return false;
  }
  if (shardName === sourceShard) {
    return true;
  }
  return shardName.startsWith(sourceShard + "/");
}

function getCollectionInfo(ns) {
  return config.collections.findOne({_id: ns});
}

function getChunks(ns, info) {
  if (info && info.uuid) {
    return config.chunks.find({uuid: info.uuid}).toArray();
  }
  return config.chunks.find({ns}).toArray();
}

function moveChunkBounds(ns, chunk) {
  const result = db.adminCommand({
    moveChunk: ns,
    bounds: [chunk.min, chunk.max],
    to: targetShard
  });
  print(`moveChunk result: ${EJSON.stringify(result)}`);
  return result.ok === 1;
}

function moveChunksForNamespace(ns, fallbackShardKey, limit) {
  const info = getCollectionInfo(ns);
  if (!info) {
    print(`No config.collections entry for ${ns}`);
    return;
  }
  const shardKey = info.key || fallbackShardKey;
  if (!shardKey || !Object.keys(shardKey).length) {
    print(`No shard key found for ${ns}`);
    return;
  }
  const allChunks = getChunks(ns, info);
  const chunks = allChunks.filter(chunk => shardMatchesSource(chunk.shard));
  const shardList = Array.from(new Set(allChunks.map(chunk => chunk.shard)));
  print(`Chunks for ${ns}: ${allChunks.length}, shards: ${EJSON.stringify(shardList)}`);
  if (!chunks.length) {
    print(`No chunks found on ${sourceShard} for ${ns}`);
    return;
  }
  let moved = 0;
  for (const chunk of chunks) {
    print(`Selected chunk ${EJSON.stringify({min: chunk.min, max: chunk.max, shard: chunk.shard})}`);
    print(`Moving ${ns} chunk bounds from ${sourceShard} to ${targetShard}`);
    try {
      if (moveChunkBounds(ns, chunk)) {
        moved += 1;
      }
    } catch (e) {
      print(`moveChunk failed for ${ns}: ${e.message}`);
    }
    if (moved >= limit) {
      break;
    }
  }
  print(`Moved ${moved}/${limit} chunks for ${ns}`);
}

function shardExists(name) {
  return !!config.shards.findOne({_id: name});
}

addTag("science");
addTag("daily");

if (!shardExists(targetShard)) {
  print(`Target shard ${targetShard} not registered. Run add_shard3 first.`);
  quit(1);
}

moveChunksForNamespace("readersDb.articles", {category: 1, aid: 1}, 5);
moveChunksForNamespace("readersDb.pop_ranks", {temporalGranularity: 1, _id: 1}, 5);

print("Done. Verify distribution with sh.status() or the monitor page.");
EOF
