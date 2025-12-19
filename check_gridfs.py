from pymongo import MongoClient
import gridfs

# 注意：这里用的是你代码中的 media 端口 27051
# 如果你没有专门配置 27051，请尝试改成 27041 (mongos) 试试
MEDIA_URI = "mongodb://localhost:27051" 
# MEDIA_URI = "mongodb://localhost:27041" # 备选

try:
    client = MongoClient(MEDIA_URI, serverSelectionTimeoutMS=2000)
    db = client["readersDb"]
    fs = gridfs.GridFS(db)
    
    print(f"Connected to {MEDIA_URI}")
    
    # 1. 列出所有文件
    print("\n--- Files in GridFS (fs.files) ---")
    all_files = list(db.fs.files.find({}, {"filename": 1, "length": 1}))
    
    if not all_files:
        print("WARNING: GridFS is EMPTY! No files found.")
    else:
        for f in all_files:
            print(f"Found file: {f['filename']} (Size: {f['length']} bytes)")

    # 2. 检查具体的 'title0' 是否存在
    print("\n--- Checking for 'title0' ---")
    if fs.exists({"filename": "title0"}):
        print("SUCCESS: File 'title0' exists.")
    else:
        print("FAILURE: File 'title0' DOES NOT EXIST in GridFS.")

except Exception as e:
    print(f"Connection Error: {e}")
    print("Please check if port 27051 is actually running in your Docker container.")