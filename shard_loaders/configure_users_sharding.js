use readersDb;

const ns = "readersDb.users";
const shardKey = { region: 1, uid: 1 };

sh.enableSharding("readersDb");
db.users.createIndex(shardKey);
sh.shardCollection(ns, shardKey);
sh.disableBalancing(ns);

const tagAssignments = [
  { shard: "shard1ReplSet", tag: "Beijing" },
  { shard: "shard2ReplSet", tag: "Hong Kong" },
];

tagAssignments.forEach(entry => sh.addShardTag(entry.shard, entry.tag));

const ranges = [
  { region: "Beijing", tag: "Beijing" },
  { region: "Hong Kong", tag: "Hong Kong" },
];

ranges.forEach(entry => {
  sh.addTagRange(
    ns,
    { region: entry.region, uid: MinKey },
    { region: entry.region, uid: MaxKey },
    entry.tag
  );
});

sh.enableBalancing(ns);
