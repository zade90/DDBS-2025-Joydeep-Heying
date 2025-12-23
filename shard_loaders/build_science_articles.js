use readersDb;

const pipeline = [
  { $match: { category: "science" } },
  { $merge: { into: "sci_articles", whenMatched: "replace" } },
];

db.articles.aggregate(pipeline);
