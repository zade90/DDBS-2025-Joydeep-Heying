use readersDb;

const pipeline = [
  { $match: { category: "science" } },
  { $merge: { into: "sci_bereads", whenMatched: "replace" } },
];

db.bereads_unsharded.aggregate(pipeline);
