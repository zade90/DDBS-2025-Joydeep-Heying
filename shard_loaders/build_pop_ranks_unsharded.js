use readersDb;

const baseProject = {
  $project: {
    date: { "$toDate": { "$toLong": "$timestamp" } },
    aid: 1,
    readOrNot: 1,
    agreeOrNot: 1,
    commentOrNot: 1,
    shareOrNot: 1,
  },
};

function buildPipeline(options) {
  return [
    baseProject,
    { $addFields: options.addFields },
    {
      $addFields: {
        timestamp: {
          $subtract: [
            { $dateFromParts: options.dateFromParts },
            new Date("1970-01-01"),
          ],
        },
      },
    },
    {
      $group: {
        _id: { timestamp: "$timestamp", aid: "$aid" },
        popScoreAgg: { $sum: "$popScore" },
      },
    },
    { $sort: { "_id.timestamp": 1, popScoreAgg: -1 } },
    { $group: { _id: "$_id.timestamp", articleAidList: { $push: "$_id.aid" } } },
    {
      $project: {
        _id: { $concat: [options.idPrefix, { $toString: "$_id" }] },
        timestamp: "$_id",
        articleAidList: { $slice: ["$articleAidList", 10] },
        temporalGranularity: options.temporalGranularity,
      },
    },
    { $out: options.outCollection },
  ];
}

const popScore = {
  $sum: [
    { $toInt: "$readOrNot" },
    { $toInt: "$agreeOrNot" },
    { $toInt: "$commentOrNot" },
    { $toInt: "$shareOrNot" },
  ],
};

const monthlyPipeline = buildPipeline({
  addFields: {
    year: { $year: "$date" },
    month: { $month: "$date" },
    popScore: popScore,
  },
  dateFromParts: { year: "$year", month: "$month" },
  idPrefix: "m",
  temporalGranularity: "monthly",
  outCollection: "montly_pop_ranks",
});

db.reads_unsharded.aggregate(monthlyPipeline, { allowDiskUse: true });

const weeklyPipeline = buildPipeline({
  addFields: {
    year: { $year: "$date" },
    month: { $month: "$date" },
    week: { $week: "$date" },
    popScore: popScore,
  },
  dateFromParts: { isoWeekYear: "$year", isoWeek: "$week" },
  idPrefix: "w",
  temporalGranularity: "weekly",
  outCollection: "weekly_pop_ranks",
});

db.reads_unsharded.aggregate(weeklyPipeline, { allowDiskUse: true });

const dailyPipeline = buildPipeline({
  addFields: {
    year: { $year: "$date" },
    month: { $month: "$date" },
    day: { $dayOfYear: "$date" },
    popScore: popScore,
  },
  dateFromParts: { year: "$year", month: "$month", day: "$day" },
  idPrefix: "d",
  temporalGranularity: "daily",
  outCollection: "daily_pop_ranks",
});

db.reads_unsharded.aggregate(dailyPipeline, { allowDiskUse: true });

db.montly_pop_ranks.find().forEach(function(doc) { db.pop_ranks_unsharded.insertOne(doc); });
db.weekly_pop_ranks.find().forEach(function(doc) { db.pop_ranks_unsharded.insertOne(doc); });
db.daily_pop_ranks.find().forEach(function(doc) { db.pop_ranks_unsharded.insertOne(doc); });

db.pop_ranks_unsharded.aggregate([
  { $sort: { timestamp: 1 } },
  { $out: "pop_ranks_unsharded" },
]);
