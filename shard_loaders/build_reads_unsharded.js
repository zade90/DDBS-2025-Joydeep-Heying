use readersDb;

const uidPipeline = [
  { $project: { uid: 1, region: 1 } },
  { $out: "uid_reg" },
];

db.users.aggregate(uidPipeline);

const withRegionPipeline = [
  {
    $lookup: {
      from: "uid_reg",
      localField: "uid",
      foreignField: "uid",
      as: "someField",
    },
  },
  { $addFields: { region: "$someField.region" } },
  { $unwind: "$region" },
  { $project: { someField: 0 } },
  { $out: "reads_unsharded" },
];

db.reads_unsharded.aggregate(withRegionPipeline, { allowDiskUse: true });

const articlePipeline = [
  { $project: { aid: 1, category: 1, timestamp: 1 } },
  { $out: "aid_cat_ts" },
];

db.articles.aggregate(articlePipeline);

const withArticlePipeline = [
  {
    $lookup: {
      from: "aid_cat_ts",
      localField: "aid",
      foreignField: "aid",
      as: "someField",
    },
  },
  { $addFields: { category: "$someField.category", article_ts: "$someField.timestamp" } },
  { $unwind: "$category" },
  { $unwind: "$article_ts" },
  { $project: { someField: 0 } },
  { $out: "reads_unsharded" },
];

db.reads_unsharded.aggregate(withArticlePipeline, { allowDiskUse: true });
