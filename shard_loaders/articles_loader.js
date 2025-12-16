use readersDb;

db.articles.createIndex({"category":1,"aid":1})
sh.shardCollection("readersDb.articles", {"category": 1, "aid": 1})
sh.disableBalancing("readersDb.articles");

sh.addShardTag("shard1ReplSet", "science");
sh.addShardTag("shard2ReplSet", "technology");

sh.addTagRange(
    "readersDb.articles",
    {"category": "science", "aid": MinKey},
    {"category": "science", "aid": MaxKey},
    "science"
);

sh.addTagRange(
    "readersDb.articles",
    {"category": "technology", "aid": MinKey},
    {"category": "technology", "aid": MaxKey},
    "technology"
);

sh.enableBalancing("readersDb.articles");