use readersDb;
db.sci_articles.createIndex({"category": 1, "aid": 1})
sh.shardCollection("readersDb.sci_articles", {"category": 1, "aid": 1})
sh.disableBalancing("readersDb.sci_articles")
sh.addShardTag("shard2ReplSet", "science_dup")
sh.addTagRange(
        "readersDb.sci_articles",
        {"category": "science", "aid": MinKey},
        {"category": "science", "aid": MaxKey},
        "science_dup"
    )
sh.enableBalancing("readersDb.sci_articles")
