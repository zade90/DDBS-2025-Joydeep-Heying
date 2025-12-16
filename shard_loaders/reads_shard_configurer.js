use readersDb;

db.reads.createIndex({"region": 1, "id": 1})
sh.shardCollection("readersDb.reads", {"region": 1, "id": 1})
sh.disableBalancing("readersDb.reads")

sh.addShardTag("shard1ReplSet", "Beijing");
sh.addShardTag("shard2ReplSet", "Hong Kong");

sh.addTagRange(
            "readersDb.reads",
            {"region": "Beijing", "id": MinKey},
            {"region": "Beijing", "id": MaxKey},
            "Beijing"
        )
sh.addTagRange(
            "readersDb.reads",
            {"region": "Hong Kong", "id": MinKey},
            {"region": "Hong Kong", "id": MaxKey},
            "Hong Kong"
        )
sh.enableBalancing("readersDb.reads")