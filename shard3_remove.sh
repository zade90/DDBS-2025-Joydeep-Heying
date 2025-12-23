#!/bin/bash
set -euo pipefail

echo "Starting graceful removal of shard3 (Robust Mode)..."

exists=$(docker exec -i mongos_router mongosh --quiet --eval "db.getSiblingDB('config').shards.findOne({_id: 'shard3ReplSet'}) ? 1 : 0")
if [ "$exists" != "1" ]; then
  echo "Shard3 not registered; nothing to remove."
  exit 0
fi

# 暂停 Balancer，防止死锁
echo "🛑 Stopping Balancer to release locks..."
docker exec -i mongos_router mongosh --quiet --eval '
    let waited = 0;
    try { db.adminCommand({ balancerStop: 1 }); } catch (e) { try { sh.stopBalancer(); } catch (e2) {} }
    while (true) {
        const status = db.adminCommand({ balancerStatus: 1 });
        if (status.mode === "off" && !status.inBalancerRound) {
            print("Balancer stopped.");
            break;
        }
        if (waited >= 30) {
            print("Balancer stop timeout; continuing.");
            printjson(status);
            break;
        }
        print("Waiting for balancer to stop...");
        sleep(1000);
        waited += 1;
    }
'

# Clean orphans
echo "Cleaning orphans on recipient shards..."
FAST_MODE=${FAST_REMOVE:-0}
SKIP_CLEANUP=${SKIP_CLEANUP:-0}

clean_shard_orphans() {
    local prefix=$1
    echo "  -> Scanning $prefix for the Primary node..."

    for node in "${prefix}_replica1" "${prefix}_replica2"; do
        cleanup_js="
            var isMaster = db.isMaster().ismaster;
            if (!isMaster) {
                print('   [SKIP] ' + '$node' + ' is Secondary.');
                quit(0);
            }
            print('   [EXEC] ' + '$node' + ' is PRIMARY. Starting cleanup...');
            
            // 要清理的集合列表
            var fastMode = ${FAST_MODE};
            var nsList = fastMode
                ? ['readersDb.articles', 'readersDb.pop_ranks']
                : ['readersDb.articles', 'readersDb.pop_ranks', 'readersDb.users', 'readersDb.reads'];
            
            nsList.forEach(ns => {
                if (fastMode) {
                    var res = db.adminCommand({ cleanupOrphaned: ns });
                    if (!res.ok) {
                        print('      Error on ' + ns + ': ' + res.errmsg);
                        return;
                    }
                    print('      ✅ Cleaned (fast) ' + ns);
                    return;
                }

                var nextKey = { };
                while (nextKey != null) {
                    // 因为 Balancer 已停，这里不会死锁
                    var res = db.adminCommand({ cleanupOrphaned: ns, startingFromKey: nextKey });
                    if (res.ok) {
                        nextKey = res.stoppedAtKey;
                    } else {
                        print('      Error on ' + ns + ': ' + res.errmsg);
                        nextKey = null;
                    }
                }
                print('      Cleaned ' + ns);
            });
        "

        tmpfile=$(mktemp)
        docker exec -i $node mongosh --quiet --eval "$cleanup_js" > "$tmpfile" 2>&1 &
        cleanup_pid=$!

        while kill -0 $cleanup_pid 2>/dev/null; do
            docker exec -i $node mongosh --quiet --eval 'const ops=db.currentOp({active:true,"command.cleanupOrphaned":{$exists:true}}).inprog || []; if(ops.length){ops.sort((a,b)=>(b.secs_running||0)-(a.secs_running||0)); const oldest=ops[0]; print("      ⏳ cleanupOrphaned ops="+ops.length+" oldest opid="+oldest.opid+" ns="+oldest.command.cleanupOrphaned+" running "+oldest.secs_running+"s");} else {print("      ⏳ cleanupOrphaned waiting for server response...");}' || true
            sleep 5
        done

        if ! wait $cleanup_pid; then
            echo "   Cleanup command failed on $node."
            cat "$tmpfile"
            rm -f "$tmpfile"
            exit 1
        fi
        cat "$tmpfile"
        rm -f "$tmpfile"
    done
}

# 执行
if [ "$SKIP_CLEANUP" = "1" ]; then
  echo "Skipping orphan cleanup (SKIP_CLEANUP=1)."
else
  clean_shard_orphans "shard1"
  clean_shard_orphans "shard2"
  echo "Orphan cleanup phase complete."
fi

echo "Adjusting Sharding Tags..."
docker exec -i mongos_router mongosh --quiet <<'EOF'
try {
  sh.addShardTag("shard1ReplSet", "science");
  sh.addShardTag("shard1ReplSet", "daily");
  
  sh.addShardTag("shard2ReplSet", "technology");
  sh.addShardTag("shard2ReplSet", "weekly_monthly");
  
  sh.removeShardTag("shard3ReplSet", "science");
  sh.removeShardTag("shard3ReplSet", "daily");
  sh.removeShardTag("shard3ReplSet", "technology");
  sh.removeShardTag("shard3ReplSet", "weekly_monthly");
  
  print("Tags adjusted: Shard3 stripped, Shard1/2 prepared.");
} catch(e) {
  print("Tag adjustment note: " + e.message);
}

try {
    var dbInfo = db.getSiblingDB("config").databases.findOne({_id: "readersDb"});
    if (dbInfo && dbInfo.primary === "shard3ReplSet") {
        print("Moving primary of readersDb to shard1ReplSet...");
        db.adminCommand({ movePrimary: "readersDb", to: "shard1ReplSet" });
    }
} catch(e) {
    print("movePrimary check error: " + e.message);
}
EOF

# 重启 Balancer
echo "Restarting Balancer and triggering drain..."
docker exec -i mongos_router mongosh --quiet --eval "sh.startBalancer()" >/dev/null

prev_state=""
echo "Waiting for Shard3 to drain..."

while true; do
  output=$(docker exec -i mongos_router mongosh --quiet --eval "EJSON.stringify(db.adminCommand({removeShard: 'shard3ReplSet'}))")
  
  state=$(echo "$output" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
  remaining=$(echo "$output" | grep -o '"remaining":{[^}]*}' || echo "calculating...")

  if [ "$state" != "$prev_state" ]; then
    echo "Status: $state | $remaining"
    prev_state="$state"
  fi

  if [ "$state" = "completed" ]; then
    echo "Shard3 drain completed successfully!"
    break
  fi

  if [[ "$output" == *"ok\":0"* ]]; then
     echo "Error during removeShard: $output"
     docker exec -i mongos_router mongosh --quiet --eval "sh.stopBalancer(); sleep(1000); sh.startBalancer();" >/dev/null
     sleep 2
     continue
  fi

  echo -n "."
  sleep 3
done

echo ""
echo "Stopping and removing shard3 containers..."
docker compose -f mongodb/docker-compose.yml stop shard3_replica1 shard3_replica2
docker compose -f mongodb/docker-compose.yml rm -f shard3_replica1 shard3_replica2

echo "Wiping data directories for Shard3..."
sudo rm -rf data/shard3_replica1/* data/shard3_replica2/*
echo "Shard3 has been removed and cleaned."
