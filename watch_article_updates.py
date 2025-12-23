from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27041"
DB_NAME = "readersDb"
WATCH_CATEGORY = "science"


def build_pipeline():
    return [{"$match": {"fullDocument.category": WATCH_CATEGORY}}]


def refresh_science_articles(database):
    database.articles.aggregate([
        {"$match": {"category": WATCH_CATEGORY}},
        {"$merge": {"into": "sci_articles", "whenMatched": "replace"}},
    ])


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    pipeline = build_pipeline()

    with db.articles.watch(pipeline) as stream:
        for event in stream:
            doc = event["fullDocument"]
            print("db.sci_articles updated", doc)
            refresh_science_articles(db)


if __name__ == "__main__":
    main()
