import pymongo
import time
import os
from datetime import datetime

MONGO_URI = 'mongodb://localhost:27041'
DB_NAME = 'readersDb'

SHARD_ROLES = {
    "shard1ReplSet": "Science / Daily",
    "shard2ReplSet": "Technology / Weekly&Monthly"
}

class ClusterMonitor:
    def __init__(self):
        self.client = pymongo.MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.admin = self.client.admin

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_server_status(self):
        """获取服务器整体状态和操作计数"""
        try:
            status = self.db.command("serverStatus")
            return status['opcounters'], status['mem'], status['connections']
        except Exception as e:
            return None, None, None

    def get_collection_distribution(self, collection_name):
        """获取集合在各个分片上的分布"""
        try:
            stats = self.db.command("collStats", collection_name)
            
            if not stats.get('sharded'):
                return None

            distribution = {}
            for shard_name, shard_data in stats['shards'].items():
                distribution[shard_name] = {
                    'count': shard_data.get('count', 0),
                    'size': shard_data.get('size', 0)
                }
            return distribution
        except Exception as e:
            return None

    def print_dashboard(self, prev_ops=None, current_ops=None, interval=1):
        self.clear_screen()
        print("="*60)
        print(f"DBMS CLUSTER MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)

        print(f"\n[1] Real-time Workload (Ops/sec)")
        print("-" * 60)
        if prev_ops and current_ops:
            headers = ["Insert", "Query", "Update", "Delete", "Command"]
            row = []
            for k in ['insert', 'query', 'update', 'delete', 'command']:
                rate = (current_ops.get(k, 0) - prev_ops.get(k, 0)) / interval
                row.append(f"{rate:>8.1f}")
            
            print(f"{headers[0]:>10} | {headers[1]:>10} | {headers[2]:>10} | {headers[3]:>10} | {headers[4]:>10}")
            print(f"{row[0]:>10} | {row[1]:>10} | {row[2]:>10} | {row[3]:>10} | {row[4]:>10}")
        else:
            print("Calculating throughput...")

        print(f"\n[2] Data Distribution & Sharding Strategy Proof")
        print("-" * 60)
        print(f"{'Collection':<15} | {'Shard Name':<15} | {'Role (Strategy)':<25} | {'Docs':<8} | {'Size (KB)':<10}")
        print("-" * 80)

        target_collections = ['articles', 'bereads', 'pop_ranks']
        
        for col_name in target_collections:
            dist = self.get_collection_distribution(col_name)
            if dist:
                for shard, data in dist.items():
                    role = SHARD_ROLES.get(shard, "Unknown")
                    size_kb = data['size'] / 1024
                    print(f"{col_name:<15} | {shard:<15} | {role:<25} | {data['count']:<8} | {size_kb:<10.2f}")
                print("-" * 80)
            else:
                print(f"{col_name:<15} | Not Sharded or Error accessing stats")
                print("-" * 80)

    def run(self):
        prev_ops, _, _ = self.get_server_status()
        
        while True:
            time.sleep(2) # 刷新间隔
            curr_ops, mem, conn = self.get_server_status()
            
            self.print_dashboard(prev_ops, curr_ops, interval=2)
            
            prev_ops = curr_ops

if __name__ == "__main__":
    monitor = ClusterMonitor()
    try:
        print("Starting Monitor...")
        monitor.run()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")