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
            # 1. 筛选用户
            {"$match": {"uid": user_id}},
            # 2. 按时间倒序
            {"$sort": {"timestamp": -1}},
            # 3. 限制条数
            {"$limit": limit},
            # 4. 关联文章表 (Join)
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "aid",
                    "foreignField": "aid",
                    "as": "article_details"
                }
            },
            # 5. 展开数组
            {"$unwind": "$article_details"},
            # 6. 格式化输出
            {
                "$project": {
                    "_id": 0,
                    "uid": 1,
                    "read_ts": "$timestamp",
                    "aid": "$aid",
                    "title": "$article_details.title",
                    "category": "$article_details.category",
                    "read_duration": "$readTimeLength" # 假设reads表有此字段，如果没有可移除
                }
            }
        ]
        return list(self.db.reads.aggregate(pipeline))

    def get_top_ranked_articles(self, granularity="daily"):
        """
        功能 2: 获取最新的热门文章详情 (基于 pop_ranks 计算结果)
        """
        pipeline = [
            # 1. 筛选粒度 (daily, weekly, monthly)
            {"$match": {"temporalGranularity": granularity}},
            # 2. 取最新的一条排行榜记录
            {"$sort": {"timestamp": -1}},
            {"$limit": 1},
            # 3. 关联获取文章详情
            # 注意: articleAidList 是一个数组，Lookup 会自动匹配数组中的所有 ID
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "articleAidList",
                    "foreignField": "aid",
                    "as": "full_article_info"
                }
            },
            # 4. 整理输出结果
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
        """
        功能 3 (基础版): 支持对任意集合执行任意 filter 查询
        允许传入原生 MongoDB 查询字典。
        """
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
        """
        功能 3 (高级版): 动态构建查询 (Dynamic Query Builder)
        根据传入的参数自动组装查询条件。
        支持参数: category, title_keyword, min_words, date_start, date_end
        """
        query = {}

        # 1. 精确匹配
        if 'category' in kwargs and kwargs['category']:
            query['category'] = kwargs['category']
        
        # 2. 模糊匹配 (Regex) - 相当于 SQL LIKE %keyword%
        if 'title_keyword' in kwargs and kwargs['title_keyword']:
            query['title'] = {'$regex': kwargs['title_keyword'], '$options': 'i'} # 'i' 忽略大小写
        
        # 3. 范围查询 (Range Query)
        if 'min_words' in kwargs:
            query['wordCount'] = {'$gte': kwargs['min_words']}
            
        # 4. 时间范围查询 (假设 timestamp 是字符串或数字，需根据实际数据类型调整)
        if 'date_start' in kwargs or 'date_end' in kwargs:
            query['timestamp'] = {}
            if 'date_start' in kwargs:
                query['timestamp']['$gte'] = kwargs['date_start']
            if 'date_end' in kwargs:
                query['timestamp']['$lte'] = kwargs['date_end']
            # 如果构建后的字典为空，删除该键
            if not query['timestamp']:
                del query['timestamp']

        print(f"Debug - Constructed Query: {query}")
        return self.execute_arbitrary_query('articles', query, limit=20)

# ==========================================
# 主程序执行入口
# ==========================================
if __name__ == "__main__":
    # 初始化
    analyzer = ReaderAnalytics()
    
    print("--- 1. Testing User History ---")
    # 替换为你数据库中真实存在的 uid (注意数据类型是字符串还是数字)
    history = analyzer.get_user_reading_history("1", limit=3)
    pprint.pprint(history)

    print("\n--- 2. Testing Popular Articles ---")
    pop_ranks = analyzer.get_top_ranked_articles("weekly")
    if pop_ranks:
        print(f"Date: {pop_ranks.get('rank_date')}")
        for art in pop_ranks.get('top_articles', []):
            print(f" - [{art['category']}] {art['title']}")
    
    print("\n--- 3. Testing Arbitrary Query (Raw) ---")
    # 示例：直接查询 Science 类别的文章，只要 ID 和 标题
    raw_results = analyzer.execute_arbitrary_query(
        collection_name='articles', 
        filter_dict={'category': 'science'}, 
        projection={'_id': 0, 'title': 1, 'category': 1},
        limit=3
    )
    pprint.pprint(raw_results)

    print("\n--- 4. Testing Arbitrary Query (Dynamic Builder) ---")
    # 示例：查找标题包含 "Quantum" 且属于 Science 分类的文章
    dynamic_results = analyzer.search_articles_dynamic(
        category='science', 
        title_keyword='Quantum'
    )
    pprint.pprint(dynamic_results)