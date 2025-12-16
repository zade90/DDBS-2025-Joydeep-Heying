from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from datetime import datetime
from bson import Int64
from fastapi.responses import StreamingResponse
import gridfs
import os
import redis
import json

# MongoDB connection
client = MongoClient("mongodb://localhost:27041/")  
MEDIA_FILES_MONGO_URI = "mongodb://localhost:27051" 
media_client = MongoClient(MEDIA_FILES_MONGO_URI)
db = client["readersDb"] 
media_db = media_client["readersDb"]  
users_collection = db["users"] 
articles_collection = db["articles"] 
pop_ranks_collection = db["pop_ranks"]
fs = gridfs.GridFS(media_db)
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)

# Initialize FastAPI app
app = FastAPI()

# Cache GET request responses using Redis
def get_cache(key: str):
    """Retrieve cached data from Redis."""
    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)
    return None

def set_cache(key: str, data: dict, ttl: int = 3600):
    """Set data in Redis with an optional time-to-live."""
    redis_client.setex(key, ttl, json.dumps(data))

# Pydantic models for request validation
class User(BaseModel):
    id: str
    uid: str
    name: str
    gender: str
    email: str
    phone: str
    dept: str
    grade: str
    language: str
    region: str
    role: str
    preferTags: str
    obtainedCredits: str

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    dept: Optional[str] = None
    grade: Optional[str] = None
    language: Optional[str] = None
    region: Optional[str] = None
    role: Optional[str] = None
    preferTags: Optional[str] = None
    obtainedCredits: Optional[str] = None

# Pydantic models for request validation
class Article(BaseModel):
    id: str
    aid: str
    title: str
    category: str
    abstract: str
    articleTags: str
    authors: str
    language: str
    text: str
    image: Optional[str] = None
    video: Optional[str] = None

class UpdateArticleRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    abstract: Optional[str] = None
    articleTags: Optional[str] = None
    authors: Optional[str] = None
    language: Optional[str] = None
    text: Optional[str] = None
    image: Optional[str] = None
    video: Optional[str] = None    

@app.post("/users/")
async def insert_user_endpoint(user: User):
    """
    Endpoint to insert a new user into the database.
    """
    user_data = user.dict()
    user_data["timestamp"] = str(int(datetime.utcnow().timestamp() * 1000))  # Current timestamp in milliseconds
    result = users_collection.insert_one(user_data)
    return {"message": "User inserted successfully", "id": str(result.inserted_id)}

@app.put("/users/{user_id}")
async def update_user_endpoint(user_id: str, update_request: UpdateUserRequest):
    """
    Endpoint to update a user's fields in the database.
    """
    update_data = update_request.dict(exclude_unset=True)
    result = users_collection.update_one({"id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated successfully", "modified_count": result.modified_count}

@app.get("/users/")
async def query_user_endpoint(id: Optional[str] = None, name: Optional[str] = None):
    """
    Endpoint to query a user by id or name.
    """
    query = {}
    if id:
        query["id"] = id
    if name:
        query["name"] = name
    user = users_collection.find_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Convert ObjectId to string for JSON serialization
    user["_id"] = str(user["_id"])
    return user


@app.get("/articles/")
async def get_article(id: Optional[str] = None, aid: Optional[str] = None):
    """
    Endpoint to retrieve an article by either `id` or `aid`.
    """
    query = {}
    if id:
        query["id"] = id
    if aid:
        query["aid"] = aid

    article = articles_collection.find_one(query)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article["_id"] = str(article["_id"])  # Convert ObjectId to string for JSON serialization
    return article

@app.post("/articles/")
async def insert_article(article: Article):
    """
    Endpoint to insert a new article into the database.
    """
    article_data = article.dict()
    article_data["timestamp"] = str(int(datetime.utcnow().timestamp() * 1000))  # Current timestamp in milliseconds
    result = articles_collection.insert_one(article_data)
    return {"message": "Article inserted successfully", "id": str(result.inserted_id)}

@app.put("/articles/{article_id}")
async def update_article(article_id: str, update_request: UpdateArticleRequest):
    """
    Endpoint to update an existing article by its `id`.
    """
    update_data = update_request.dict(exclude_unset=True)
    result = articles_collection.update_one({"id": article_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Article updated successfully", "modified_count": result.modified_count}


@app.get("/poprank/timestamps/")
async def get_timestamps_by_granularity(temporal_granularity: str):
    """
    Get a list of timestamps for all documents with the given temporal granularity.
    """
    # Validate input
    if temporal_granularity not in ["weekly", "daily", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid temporal granularity. Must be 'weekly', 'daily', or 'monthly'.")

    # Query the database
    documents = pop_ranks_collection.find({"temporalGranularity": temporal_granularity}, {"timestamp": 1, "_id": 0})
    timestamps = [doc["timestamp"] for doc in documents]

    if not timestamps:
        raise HTTPException(status_code=404, detail="No documents found for the given temporal granularity.")

    return {"temporalGranularity": temporal_granularity, "timestamps": timestamps}

@app.get("/poprank/document/")
async def get_document_by_granularity_and_timestamp(temporal_granularity: str, ts: str):
    """
    Get a full document by temporal granularity and timestamp.
    """
    # Validate input
    if temporal_granularity not in ["weekly", "daily", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid temporal granularity. Must be 'weekly', 'daily', or 'monthly'.")
    
    try:
        ts = Int64(ts)
    except:
        raise HTTPException(status_code=400, detail="Invalid timestamp")


    # Query the database
    document = pop_ranks_collection.find_one(
        {"temporalGranularity": temporal_granularity, "timestamp": ts}
    )

    if not document:
        raise HTTPException(status_code=404, detail="No document found for the given query.")

    # Convert ObjectId and nested fields for JSON serialization
    document["_id"] = str(document["_id"])
    return document

# @app.get("/files/{filename}")
# async def stream_file(filename: str):
#     """
#     Stream a file from GridFS to the client.
#     """

#     try:
#         # Retrieve the file from GridFS
#         file = fs.get_last_version(filename)

#         # Generate a streaming response
#         def file_iterator():
#             while chunk := file.read(1024 * 1024):  # Read in 1 MB chunks
#                 yield chunk

#         # Determine the content type based on file extension
#         ext = os.path.splitext(filename)[-1].lower()
#         content_type = {
#             ".jpg": "image/jpeg",
#             ".jpeg": "image/jpeg",
#             ".png": "image/png",
#             ".gif": "image/gif",
#             ".mp4": "video/mp4",
#             ".txt": "text/plain",
#             ".flv": "video/x-flv",
#         }.get(ext, "application/octet-stream")  # Default to binary data if type unknown

#         # Create and return the StreamingResponse
#         return StreamingResponse(file_iterator(), media_type=content_type)
    
#     except gridfs.errors.NoFile:
#         raise HTTPException(status_code=404, detail=f"File '{filename}' not found in GridFS.")

@app.get("/files/{filename}")
async def stream_file(filename: str):
    """
    Stream a file from GridFS to the client.
    """

    try:
        # Retrieve the file from GridFS
        file = fs.get_last_version(filename)

        # Generate a streaming response
        def file_iterator():
            while chunk := file.read(1024 * 1024):  # Read in 1 MB chunks
                yield chunk

        # Determine the content type based on file extension
        ext = os.path.splitext(filename)[-1].lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".txt": "text/plain",
            ".flv": "video/x-flv",
        }.get(ext, "application/octet-stream")  # Default to binary data if type unknown

        # Create and return the StreamingResponse without Content-Disposition
        response = StreamingResponse(file_iterator(), media_type=content_type)
        response.headers["Content-Disposition"] = "inline"
        return response
    
    except gridfs.errors.NoFile:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in GridFS.")
    

@app.get("/")
def read_root():
    return {"Hello": "World"}


# uvicorn main:app --host 0.0.0.0 --port 20000