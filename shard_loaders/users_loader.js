
use readersDb;

sh.enableSharding("readersDb");

db.users.createIndex({"region": 1, "uid": 1});

sh.shardCollection("readersDb.users", {"region": 1, "uid": 1});

sh.disableBalancing("readersDb.users");

sh.addShardTag("shard1ReplSet", "Beijing");
sh.addShardTag("shard2ReplSet", "Hong Kong");

sh.addTagRange(
    "readersDb.users",
    {"region": "Beijing", "uid": MinKey},
    {"region": "Beijing", "uid": MaxKey},
    "Beijing"
);

sh.addTagRange(
    "readersDb.users",
    {"region": "Hong Kong", "uid": MinKey},
    {"region": "Hong Kong", "uid": MaxKey},
    "Hong Kong"
);


sh.enableBalancing("readersDb.users");