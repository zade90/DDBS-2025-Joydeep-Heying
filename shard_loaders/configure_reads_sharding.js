use readersDb;

const ns = "readersDb.reads";
const shardKey = { region: 1, id: 1 };

db.reads.createIndex(shardKey);
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
    { region: entry.region, id: MinKey },
    { region: entry.region, id: MaxKey },
    entry.tag
  );
});

sh.enableBalancing(ns);
