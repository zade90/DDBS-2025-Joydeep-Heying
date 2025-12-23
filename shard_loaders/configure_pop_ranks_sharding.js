use readersDb;

const ns = "readersDb.pop_ranks";
const shardKey = { temporalGranularity: 1, _id: 1 };

db.pop_ranks.createIndex(shardKey);
sh.shardCollection(ns, shardKey);
sh.disableBalancing(ns);

sh.addShardTag("shard1ReplSet", "daily");
sh.addShardTag("shard2ReplSet", "weekly_monthly");

const ranges = [
  { granularity: "daily", tag: "daily" },
  { granularity: "weekly", tag: "weekly_monthly" },
  { granularity: "monthly", tag: "weekly_monthly" },
];

ranges.forEach(entry => {
  sh.addTagRange(
    ns,
    { temporalGranularity: entry.granularity, _id: MinKey },
    { temporalGranularity: entry.granularity, _id: MaxKey },
    entry.tag
  );
});

sh.enableBalancing(ns);
