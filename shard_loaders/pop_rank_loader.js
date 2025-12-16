use readersDb;
db.reads_unsharded.aggregate([

    { $project: { date: {"$toDate": {"$toLong": "$timestamp"}}, aid: 1, readOrNot: 1, agreeOrNot: 1, commentOrNot: 1, shareOrNot: 1} },
    { $addFields: {
        year: { $year: "$date" },
        month: { $month: "$date" },
        popScore: {$sum: [{$toInt: "$readOrNot"}, {$toInt: "$agreeOrNot"}, {$toInt: "$commentOrNot"}, {$toInt: "$shareOrNot"}]}}
    },

    { $addFields: { timestamp: { $subtract: [ { $dateFromParts: { 'year' : "$year", 'month' : "$month"} }, new Date("1970-01-01") ] }}},

    // Group by year, month, aid and compute popularity score
    {
        $group: {
            _id: { "timestamp": "$timestamp", "aid": "$aid"},
            popScoreAgg: { $sum: "$popScore" }
        }
    },

    // sort by popScore each month
    { $sort: {"_id.timestamp": 1, "popScoreAgg": -1} },

    // store all articles in sorted order in array for each month
    {
        $group: {
            _id: "$_id.timestamp",
            articleAidList: {$push: "$_id.aid"}
        }
    },

    { 
        $project: { 
            _id: {$concat: ["m", { $toString: "$_id" }]}, 
            timestamp: "$_id", 
            articleAidList: { $slice: ["$articleAidList", 10]},
            temporalGranularity: "monthly"
            }
    },

    {"$out": "montly_pop_ranks"}
],
{ allowDiskUse: true })

db.reads_unsharded.aggregate([
    { $project: { date: {"$toDate": {"$toLong": "$timestamp"}}, aid: 1, readOrNot: 1, agreeOrNot: 1, commentOrNot: 1, shareOrNot: 1} },

    { $addFields: {
        year: { $year: "$date" },
        month: { $month: "$date" },
        week: {$week: "$date"},
        popScore: {$sum: [{$toInt: "$readOrNot"}, {$toInt: "$agreeOrNot"}, {$toInt: "$commentOrNot"}, {$toInt: "$shareOrNot"}]}}
    },

    { $addFields: { timestamp: { $subtract: [ { $dateFromParts: { 'isoWeekYear' : "$year", 'isoWeek' : "$week"} }, new Date("1970-01-01") ] }}},

    // Group by year, month, aid and compute popularity score
    {
        $group: {
            _id: { "timestamp": "$timestamp", "aid": "$aid"},
            popScoreAgg: { $sum: "$popScore" }
        }
    },

    // sort by popScore each month
    { $sort: {"_id.timestamp": 1, "popScoreAgg": -1} },

    // store all articles in sorted order in array for each month
    {
        $group: {
            _id: "$_id.timestamp",
            articleAidList: {$push: "$_id.aid"}
        }
    },
    { 
        $project: { 
            _id: {$concat: ["w", { $toString: "$_id" }]}, 
            timestamp: "$_id", 
            articleAidList: { $slice: ["$articleAidList", 10]},
            temporalGranularity: "weekly"
            }
    },

    {"$out": "weekly_pop_ranks"}
],
{ allowDiskUse: true })


db.reads_unsharded.aggregate([
    // project relevant fields from db.read
    { $project: { date: {"$toDate": {"$toLong": "$timestamp"}}, aid: 1, readOrNot: 1, agreeOrNot: 1, commentOrNot: 1, shareOrNot: 1} },

    // add year and month fields
    { $addFields: {
        year: { $year: "$date" },
        month: { $month: "$date" },
        day: {$dayOfYear: "$date" },
        popScore: {$sum: [{$toInt: "$readOrNot"}, {$toInt: "$agreeOrNot"}, {$toInt: "$commentOrNot"}, {$toInt: "$shareOrNot"}]}}
    },

    // add unix timestamp defined only by yr and mth
    { $addFields: { timestamp: { $subtract: [ { $dateFromParts: { 'year' : "$year", 'month' : "$month", 'day': "$day"} }, new Date("1970-01-01") ] }}},

    // Group by year, month, aid and compute popularity score
    {
        $group: {
            _id: { "timestamp": "$timestamp", "aid": "$aid"},
            popScoreAgg: { $sum: "$popScore" }
        }
    },

    // sort by popScore each month
    { $sort: {"_id.timestamp": 1, "popScoreAgg": -1} },

    // store all articles in sorted order in array for each month
    {
        $group: {
            _id: "$_id.timestamp",
            articleAidList: {$push: "$_id.aid"}
        }
    },

    // keep only top five articles in array
    { 
        $project: { 
            _id: {$concat: ["d", { $toString: "$_id" }]}, 
            timestamp: "$_id", 
            articleAidList: { $slice: ["$articleAidList", 10]},
            temporalGranularity: "daily"
            }
    },

    // output
    {"$out": "daily_pop_ranks"}
],
{ allowDiskUse: true })


db.montly_pop_ranks.find().forEach( function(doc) { db.pop_ranks_unsharded.insertOne(doc) })
db.weekly_pop_ranks.find().forEach( function(doc) { db.pop_ranks_unsharded.insertOne(doc) })
db.daily_pop_ranks.find().forEach( function(doc) { db.pop_ranks_unsharded.insertOne(doc) })
db.pop_ranks_unsharded.aggregate([ {$sort: {timestamp:1}}, {$out: "pop_ranks_unsharded"} ])