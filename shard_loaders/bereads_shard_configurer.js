use readersDb;

db.bereads.createIndex({"category":1,"aid":1})
sh.shardCollection("readersDb.bereads", {"category": 1, "aid": 1})
sh.disableBalancing("readersDb.bereads");

sh.addShardTag("shard1ReplSet", "science");
sh.addShardTag("shard2ReplSet", "technology");

sh.addTagRange(
    "readersDb.bereads",
    {"category": "science", "aid": MinKey},
    {"category": "science", "aid": MaxKey},
    "science"
);

sh.addTagRange(
    "readersDb.bereads",
    {"category": "technology", "aid": MinKey},
    {"category": "technology", "aid": MaxKey},
    "technology"
);

sh.enableBalancing("readersDb.bereads");