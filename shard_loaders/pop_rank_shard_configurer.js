use readersDb;

db.pop_ranks.createIndex({"_id": 1,"temporalGranularity":1})
sh.shardCollection("readersDb.pop_ranks", {"temporalGranularity":1,"_id": 1})
sh.disableBalancing("readersDb.pop_ranks")

sh.addShardTag("shard1ReplSet", "daily");
sh.addShardTag("shard2ReplSet", "weekly_monthly");

sh.addTagRange(
            "readersDb.pop_ranks",
            {"temporalGranularity":"daily","_id": MinKey},
            {"temporalGranularity":"daily","_id": MaxKey},
            "daily"
        )

sh.addTagRange(
            "readersDb.pop_ranks",
            {"temporalGranularity":"weekly","_id": MinKey},
            {"temporalGranularity":"weekly","_id": MaxKey},
            "weekly_monthly"
        )  

sh.addTagRange(
    "readersDb.pop_ranks",
    { "temporalGranularity": "monthly", "_id": MinKey },
    { "temporalGranularity": "monthly", "_id": MaxKey },
    "weekly_monthly"
);        
    
sh.enableBalancing("readersDb.pop_ranks")