
use readersDb;
db.articles.aggregate([
    { $match: {category: "science"}},
    { $merge: {into: "sci_articles", whenMatched: "replace"}}
])