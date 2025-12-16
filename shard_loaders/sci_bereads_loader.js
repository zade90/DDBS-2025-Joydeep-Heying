use readersDb;
db.bereads_unsharded.aggregate([
    { $match: {category: "science"}},
    { $merge: {into: "sci_bereads", whenMatched: "replace"}}
])