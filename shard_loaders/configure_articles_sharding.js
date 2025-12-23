use readersDb;

const ns = "readersDb.articles";
const shardKey = { category: 1, aid: 1 };

db.articles.createIndex(shardKey);
sh.shardCollection(ns, shardKey);
sh.disableBalancing(ns);

const tagAssignments = [
  { shard: "shard1ReplSet", tag: "science" },
  { shard: "shard2ReplSet", tag: "technology" },
];

tagAssignments.forEach(entry => sh.addShardTag(entry.shard, entry.tag));

const ranges = [
  { category: "science", tag: "science" },
  { category: "technology", tag: "technology" },
];

ranges.forEach(entry => {
  sh.addTagRange(
    ns,
    { category: entry.category, aid: MinKey },
    { category: entry.category, aid: MaxKey },
    entry.tag
  );
});

sh.enableBalancing(ns);
