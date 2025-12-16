import os
from pymongo import MongoClient
import gridfs

# MongoDB connection details 
DATABASE_NAME = "readersDb"  
# ARTICLES_DIR_PATH = "db-generation/test_articles/"
ARTICLES_DIR_PATH = "db-generation/articles/"

# MEDIA_FILES_MONGO_URI = "mongodb://localhost:27051" 
MEDIA_FILES_MONGO_URI = "mongodb://localhost:27041" 


media_client = MongoClient(MEDIA_FILES_MONGO_URI)
db = media_client[DATABASE_NAME]
bucket = gridfs.GridFS(db)

def bulk_upload_images(directory):
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    if not files:
        print(f"No files found in directory {directory}.")
        return

    for file_name in files:
        
        file_path = os.path.join(directory, file_name)
        with open(file_path, "rb") as file:
            if bucket.exists({"filename": file_name}):
                print(f"File {file_name} already exists in GridFS. Skipping...")
            else:
                file_id = bucket.put(file, filename=file_name)
                print(f"Uploaded {file_name} with file_id {file_id}")

if __name__ == "__main__":
    for dir in os.listdir(ARTICLES_DIR_PATH):
        article_path = os.path.join(ARTICLES_DIR_PATH, dir)
        bulk_upload_images(article_path)

