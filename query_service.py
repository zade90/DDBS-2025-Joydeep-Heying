import pymongo
from pymongo import MongoClient
import pprint
from datetime import datetime

class ReaderAnalytics:
    def __init__(self, connection_string='mongodb://localhost:27041', db_name='readersDb'):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]

    def get_user_reading_history(self, user_id, limit=10):
        """
        功能 1: 获取用户阅读历史，并关联文章详细信息
        """
        pipeline = [
            {"$match": {"uid": user_id}},
            {"$sort": {"timestamp": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "aid",
                    "foreignField": "aid",
                    "as": "article_details"
                }
            },
            {"$unwind": "$article_details"},
            {
                "$project": {
                    "_id": 0,
                    "uid": 1,
                    "read_ts": "$timestamp",
                    "aid": "$aid",
                    "title": "$article_details.title",
                    "category": "$article_details.category",
                    "read_duration": "$readTimeLength" 
                }
            }
        ]
        return list(self.db.reads.aggregate(pipeline))

    def get_top_ranked_articles(self, granularity="daily"):
        """
        获取最新的热门文章详情
        """
        pipeline = [
            {"$match": {"temporalGranularity": granularity}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 1},
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "articleAidList",
                    "foreignField": "aid",
                    "as": "full_article_info"
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "rank_date": "$timestamp",
                    "type": "$temporalGranularity",
                    "top_articles": {
                        "$map": {
                            "input": "$full_article_info",
                            "as": "art",
                            "in": {
                                "aid": "$$art.aid",
                                "title": "$$art.title",
                                "category": "$$art.category",
                                "image": "$$art.imagePath"
                            }
                        }
                    }
                }
            }
        ]
        
        results = list(self.db.pop_ranks.aggregate(pipeline))
        return results[0] if results else None

    def execute_arbitrary_query(self, collection_name, filter_dict=None, projection=None, limit=0):
        if filter_dict is None:
            filter_dict = {}
        
        try:
            cursor = self.db[collection_name].find(filter_dict, projection)
            if limit > 0:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"Query Error: {e}")
            return []

    def search_articles_dynamic(self, **kwargs):
        query = {}

        if 'category' in kwargs and kwargs['category']:
            query['category'] = kwargs['category']
        
        if 'title_keyword' in kwargs and kwargs['title_keyword']:
            query['title'] = {'$regex': kwargs['title_keyword'], '$options': 'i'} # 'i' 忽略大小写
        
        if 'min_words' in kwargs:
            query['wordCount'] = {'$gte': kwargs['min_words']}
            
        if 'date_start' in kwargs or 'date_end' in kwargs:
            query['timestamp'] = {}
            if 'date_start' in kwargs:
                query['timestamp']['$gte'] = kwargs['date_start']
            if 'date_end' in kwargs:
                query['timestamp']['$lte'] = kwargs['date_end']
            if not query['timestamp']:
                del query['timestamp']

        print(f"Debug - Constructed Query: {query}")
        return self.execute_arbitrary_query('articles', query, limit=20)

if __name__ == "__main__":
    analyzer = ReaderAnalytics()
    
    print("--- 1. Testing User History ---")
    history = analyzer.get_user_reading_history("1", limit=3)
    pprint.pprint(history)

    print("\n--- 2. Testing Popular Articles ---")
    pop_ranks = analyzer.get_top_ranked_articles("weekly")
    if pop_ranks:
        print(f"Date: {pop_ranks.get('rank_date')}")
        for art in pop_ranks.get('top_articles', []):
            print(f" - [{art['category']}] {art['title']}")
    
    print("\n--- 3. Testing Arbitrary Query (Raw) ---")
    raw_results = analyzer.execute_arbitrary_query(
        collection_name='articles', 
        filter_dict={'category': 'science'}, 
        projection={'_id': 0, 'title': 1, 'category': 1},
        limit=3
    )
    pprint.pprint(raw_results)

    print("\n--- 4. Testing Arbitrary Query (Dynamic Builder) ---")
    dynamic_results = analyzer.search_articles_dynamic(
        category='science', 
        title_keyword='Quantum'
    )
    pprint.pprint(dynamic_results)