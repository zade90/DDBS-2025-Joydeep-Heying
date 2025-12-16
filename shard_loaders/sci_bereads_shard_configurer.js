use readersDb;
db.sci_bereads.createIndex({"category": 1, "aid": 1})
sh.shardCollection("readersDb.sci_bereads", {"category": 1, "aid": 1})
sh.disableBalancing("readersDb.sci_bereads")
sh.addShardTag("shard2ReplSet", "science_dup")
sh.addTagRange(
        "readersDb.sci_bereads",
        {"category": "science", "aid": MinKey},
        {"category": "science", "aid": MaxKey},
        "science_dup"
    )
sh.enableBalancing("readersDb.sci_bereads")