import pymongo
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27041')
db = client.readersDb

with db.articles.watch(
        [{'$match': {'fullDocument.category': 'science'}}]) as stream:
    for change in stream:
        print("db.sci_articles updated", change['fullDocument'])

        db.articles.aggregate([
            {"$match": {"category": "science"}},
            {"$merge": {"into": "sci_articles", "whenMatched":"replace"}}
        ])