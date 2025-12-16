use readersDb;

db.reads_unsharded.aggregate(
    [
        // group by aid and create new fields with aggregated counts and arrays
        {
            $group: {
                _id: "$aid",
                category: { $first: "$category" },
                timestamp: { $first: "$article_ts" },
                readNum: { $sum: {$toInt: "$readOrNot" } },
                readUidList: { $addToSet: { $cond: { if: { $eq: ["$readOrNot","1"] }, then: "$uid", else: "$$REMOVE"} } },
                commentNum: { $sum: {$toInt: "$commentOrNot" } },
                commentUidList: { $addToSet: { $cond: { if: { $eq: ["$commentOrNot","1"] }, then: "$uid", else: "$$REMOVE"} } },
                agreeNum: { $sum: {$toInt: "$agreeOrNot" } },
                agreeUidList: { $addToSet: { $cond: { if: { $eq: ["$agreeOrNot","1"] }, then: "$uid", else: "$$REMOVE"} } },
                shareNum: { $sum: {$toInt: "$shareOrNot" } },
                shareUidList: { $addToSet: { $cond: { if: { $eq: ["$shareOrNot","1"] }, then: "$uid", else: "$$REMOVE"} } },
            }
        },

        // Modify aid from integer to string
        { $addFields: { "aid": {$concat: [ "a", "$_id" ]}}},

        { $out: "bereads_unsharded"}
    ],
    { allowDiskUse: true })