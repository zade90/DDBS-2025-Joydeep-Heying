use readersDb;

const pipeline = [
  {
    $group: {
      _id: "$aid",
      category: { $first: "$category" },
      timestamp: { $first: "$article_ts" },
      readNum: { $sum: { $toInt: "$readOrNot" } },
      readUidList: {
        $addToSet: {
          $cond: { if: { $eq: ["$readOrNot", "1"] }, then: "$uid", else: "$$REMOVE" },
        },
      },
      commentNum: { $sum: { $toInt: "$commentOrNot" } },
      commentUidList: {
        $addToSet: {
          $cond: { if: { $eq: ["$commentOrNot", "1"] }, then: "$uid", else: "$$REMOVE" },
        },
      },
      agreeNum: { $sum: { $toInt: "$agreeOrNot" } },
      agreeUidList: {
        $addToSet: {
          $cond: { if: { $eq: ["$agreeOrNot", "1"] }, then: "$uid", else: "$$REMOVE" },
        },
      },
      shareNum: { $sum: { $toInt: "$shareOrNot" } },
      shareUidList: {
        $addToSet: {
          $cond: { if: { $eq: ["$shareOrNot", "1"] }, then: "$uid", else: "$$REMOVE" },
        },
      },
    },
  },
  { $addFields: { aid: { $concat: ["a", "$_id"] } } },
  { $out: "bereads_unsharded" },
];

db.reads_unsharded.aggregate(pipeline, { allowDiskUse: true });
