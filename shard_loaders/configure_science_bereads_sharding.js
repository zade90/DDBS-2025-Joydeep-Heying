use readersDb;

const ns = "readersDb.sci_bereads";
const shardKey = { category: 1, aid: 1 };

db.sci_bereads.createIndex(shardKey);
sh.shardCollection(ns, shardKey);
sh.disableBalancing(ns);

sh.addShardTag("shard2ReplSet", "science_dup");
sh.addTagRange(
  ns,
  { category: "science", aid: MinKey },
  { category: "science", aid: MaxKey },
  "science_dup"
);

sh.enableBalancing(ns);
