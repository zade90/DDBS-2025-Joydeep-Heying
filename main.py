from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
from pydantic import BaseModel
import os
import gridfs
from flask import Flask, render_template, send_file, Response
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from io import BytesIO
import redis


client = MongoClient("mongodb://localhost:27041/")  
MEDIA_FILES_MONGO_URI = "mongodb://localhost:27051" 
media_client = MongoClient(MEDIA_FILES_MONGO_URI)
db = client["readersDb"] 
media_db = media_client["readersDb"]  
users_collection = db["users"] 
articles_collection = db["articles"] 
pop_ranks_collection = db["pop_ranks"]
reads_collection = db["reads"]
fs = gridfs.GridFS(media_db)
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
# Initialize Flask app
app = Flask(__name__)

# Set up folder for file uploads (optional, for handling images and videos)
app.config['UPLOAD_FOLDER'] = 'uploads'


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


@app.route("/")
def home():
    return render_template("base.html")

@app.route("/users/")
def users_page():
    users = list(users_collection.find())
    for user in users:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string for JSON serialization
    return render_template("users.html", users=users)


@app.route("/users/edit/<user_id>/", methods=["GET", "POST"])
def edit_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404

    # If it's a POST request, update the user data
    if request.method == "POST":
        updated_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "gender": request.form.get("gender"),
            "dept": request.form.get("dept"),
            "grade": request.form.get("grade"),
            "language": request.form.get("language"),
            "region": request.form.get("region"),
            "role": request.form.get("role"),
            "preferTags": request.form.get("preferTags"),
            "obtainedCredits": request.form.get("obtainedCredits")
        }

        # Update the user in the database
        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})

        # Redirect after POST to avoid re-submitting the form on refresh
        return redirect(url_for('users_page'))

    # If it's a GET request, render the form with the current user data
    return render_template("edit_user.html", user=user)

@app.route("/articles/")
def articles_page():
    search_query = request.args.get('search', '').strip()  # Default to empty string if no query
    query_filter = {}
    if search_query:
        query_filter["title"] = search_query  # Perform exact match search for title

    if search_query:
        articles = list(db.articles.find(query_filter))
    else:
        articles = list(db.articles.find().limit(30))  # Adjust the limit as needed

    for article in articles:
        image_filename = article.get("image")
        image_filename = image_filename.split(",")[0]  # Assuming the image field is a comma-separated list
        if image_filename:
            article["image_url"] = f"/files/{image_filename}"
        else:
            article["image_url"] = None  # Default to None if no image is found

    return render_template("articles.html", articles=articles, search_query=search_query)

def format_timestamp(timestamp_ms):
    # Convert from milliseconds to seconds
    timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)  # Convert to seconds
    return timestamp.strftime('%B %d, %Y, %I:%M %p')  # Format: January 01, 2024, 12:00 PM

@app.route("/poprank/", methods=["GET", "POST"])
def poprank_page():
    # Handle form submission (for granularity)
    if request.method == "POST":
        granularity = request.form.get("granularity")
        if granularity:
            # Fetch the available PopRank data for the selected granularity
            poprank_data = list(pop_ranks_collection.find({"temporalGranularity": granularity}))
            
            # For each PopRank record, fetch the corresponding articles using the articleAidList
            all_articles = []
            for record in poprank_data:
                article_ids = record.get("articleAidList", [])
                articles = []
                for article_id in article_ids:
                    article_id_prefixed = f"a{article_id}"  # Prefix with "a" as required
                    article = articles_collection.find_one({"aid": article_id_prefixed})
                    if article:
                        articles.append(article)  # Add the article to the list
                
                # Convert the timestamp to a human-readable date format
                formatted_date = format_timestamp(record.get("timestamp"))

                all_articles.append({
                    "timestamp": formatted_date,  # Use the formatted date here
                    "articles": articles,
                    "timestamp_ms": record.get("timestamp")  # Store the timestamp in milliseconds
                })
            
            return render_template("poprank_display.html", granularity=granularity, all_articles=all_articles)
    
    # If it's a GET request, show the form to choose granularity
    return render_template("poprank_select_granularity.html")

# Route to display ranking for a specific granularity and timestamp
@app.route("/poprank/<granularity>/<timestamp>/")
def poprank_ranking(granularity, timestamp):
    # Convert timestamp string to integer
    timestamp_ms = int(timestamp)
    print(timestamp_ms)
    # Fetch the PopRank record for the given granularity and timestamp
    record = pop_ranks_collection.find_one({
        "temporalGranularity": granularity,
        "timestamp": timestamp_ms
    })
    print(record)
    if not record:
        return "PopRank record not found", 404
    
    # Fetch articles using articleAidList
    article_ids = record.get("articleAidList", [])
    articles = []
    for article_id in article_ids:
        article_id_prefixed = f"a{article_id}"  # Prefix with "a" as required
        article = articles_collection.find_one({"id": article_id_prefixed})
        if article:
            articles.append(article)
    
    # Convert timestamp to human-readable format
    formatted_date = format_timestamp(record.get("timestamp"))

    return render_template("poprank_ranking.html", granularity=granularity, timestamp=formatted_date, articles=articles)

    # If it's a GET request, show the form to choose granularity
    return render_template("poprank_select_granularity.html")
# Route to add a new user
@app.route("/users/add/", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        # Get data from the form
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        gender = request.form.get("gender")
        dept = request.form.get("dept")
        grade = request.form.get("grade")
        language = request.form.get("language")
        region = request.form.get("region")
        role = request.form.get("role")
        preferTags = request.form.get("preferTags")
        obtainedCredits = request.form.get("obtainedCredits")
        
        # Generate a new user id and timestamp
        user_id = f"u{str(int(datetime.utcnow().timestamp()))[-4:]}"  # Generate a simple user ID (u1234)
        timestamp = str(int(datetime.utcnow().timestamp() * 1000))  # Current timestamp in milliseconds
        uid = str(int(datetime.utcnow().timestamp() * 1000))  # Use timestamp as uid for simplicity
        
        # Create the user data
        user_data = {
            "id": user_id,
            "uid": uid,
            "name": name,
            "gender": gender,
            "email": email,
            "phone": phone,
            "dept": dept,
            "grade": grade,
            "language": language,
            "region": region,
            "role": role,
            "preferTags": preferTags,
            "obtainedCredits": obtainedCredits,
            "timestamp": timestamp
        }

        # Insert into the database
        users_collection.insert_one(user_data)

        # Redirect back to the users page
        return redirect(url_for('users_page'))

    return render_template("add_user.html")

@app.route("/users/delete/<user_id>/", methods=["GET"])
def delete_user(user_id):
    users_collection.delete_one({"_id": ObjectId(user_id)})
    return redirect(url_for('users_page'))

@app.route('/files/<filename>')
def serve_file(filename):
    # Fetch file metadata from fs.files collection
    file = media_db.fs.files.find_one({"filename": filename})
    
    if not file:
        return "File not found", 404
    
    # Fetch the file data from fs.chunks collection
    file_id = file['_id']
    grid_out = fs.get(file_id)
    
    # Determine content type
    ext = filename.split('.')[-1].lower()
    content_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "flv": "video/x-flv",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")
    
    # Return the file as a streaming response
    return Response(grid_out, content_type=content_type)


@app.route("/articles/add/", methods=["GET", "POST"])
def add_article():
    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        abstract = request.form.get("abstract")
        article_tags = request.form.get("articleTags")
        authors = request.form.get("authors")
        language = request.form.get("language")
        
        # Handle file uploads (text, image, video)
        text = request.files.get("text")
        if text:
            text_filename = secure_filename(text.filename)
            text.save(os.path.join(app.config['UPLOAD_FOLDER'], text_filename))
        else:
            text_filename = None

        article_data = {
            "title": title,
            "category": category,
            "abstract": abstract,
            "articleTags": article_tags,
            "authors": authors,
            "language": language,
            "timestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "text": text_filename,
            "image": "",
            "video": "",
        }
        
        articles_collection.insert_one(article_data)
        return redirect(url_for('articles_page'))

    return render_template("add_article.html")

@app.route("/articles/edit/<article_id>/", methods=["GET", "POST"])
def edit_article(article_id):
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    if not article:
        return "Article not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        abstract = request.form.get("abstract")
        article_tags = request.form.get("articleTags")
        authors = request.form.get("authors")
        language = request.form.get("language")
        
        # Handle file uploads (text, image, video)
        text = request.files.get("text")
        if text:
            text_filename = secure_filename(text.filename)
            text.save(os.path.join(app.config['UPLOAD_FOLDER'], text_filename))
        else:
            text_filename = article.get("text", None)
        
        existing_images = article.get("image", "")
        video_filename = article.get("video", None)

        # Update article data
        updated_data = {
            "title": title,
            "category": category,
            "abstract": abstract,
            "articleTags": article_tags,
            "authors": authors,
            "language": language,
            "timestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "text": text_filename,
            "image": existing_images,
            "video": video_filename,
        }

        articles_collection.update_one({"_id": ObjectId(article_id)}, {"$set": updated_data})
        return redirect(url_for('articles_page'))

    return render_template("edit_article.html", article=article)


from datetime import datetime


@app.route("/articles/delete/<article_id>/", methods=["POST"])
def delete_article(article_id):
    # Find the article by ID
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    
    if not article:
        return "Article not found", 404

    # Delete the article
    articles_collection.delete_one({"_id": ObjectId(article_id)})

    # Redirect to the articles list page after deletion
    return redirect(url_for('articles_page'))


@app.route("/articles/<article_id>/")
def article_detail(article_id):
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    if not article:
        return "Article not found", 404
    
    # Convert ObjectId to string for JSON serialization
    article["_id"] = str(article["_id"])

    # Convert timestamp to a human-readable format
    timestamp_ms = int(article.get("timestamp", 0))
    if timestamp_ms:
        timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)  # Convert to seconds
        article["human_readable_timestamp"] = timestamp.strftime('%B %d, %Y, %I:%M %p')  # Format: January 01, 2024, 12:00 PM
    else:
        article["human_readable_timestamp"] = "Date not available"
    
    # Add image URLs and other assets
    image_filenames_list = article.get("image", "").split(",")[0:-1]  # Split by comma for multiple images
    image_urls = []  # List to store URLs of images
    
    for image_filename in image_filenames_list:
        if image_filename:
            image_file = fs.find_one({"filename": image_filename})
            if image_file:
                image_urls.append(f"/files/{image_filename}")  # Add URL to list
            else:
                image_urls.append(None)  # If image not found, append None
        else:
            image_urls.append(None)  # If no image filename in list, append None
    
    article["image_urls"] = image_urls  # Store the list of image URLs

    # Fetch article text from GridFS if it's stored there
    text_filename = article.get("text")  # Assuming 'text' field stores filename in GridFS
    if text_filename:
        text_file = fs.find_one({"filename": text_filename})
        if text_file:
            article["content"] = text_file.read().decode('utf-8')  # Read text and decode
        else:
            article["content"] = "Content not found."
    else:
        article["content"] = "No text content available."  # If no text field

    video_filename = article.get("video")  # Assuming 'video' field stores filename in GridFS
    if video_filename:
        video_file = fs.find_one({"filename": video_filename})
        if video_file:
            article["video_url"] = f"/files/{video_filename}"  # Set video URL for playback
        else:
            article["video_url"] = None  # If video not found, set to None
    else:
        article["video_url"] = None  # If no video filename, set to None

    return render_template("article_detail.html", article=article)


@app.route("/users/<uid>/history/")
def user_history(uid):
    user = users_collection.find_one({"uid": uid})
    
    pipeline = [
        {"$match": {"uid": uid}},
        {"$sort": {"timestamp": -1}},
        {"$limit": 50},
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
                "timestamp": 1,
                "aid": 1,
                "readTimeLength": 1,
                "title": "$article_details.title",
                "category": "$article_details.category",
                "image": "$article_details.image"
            }
        }
    ]
    
    history_records = list(reads_collection.aggregate(pipeline))
    
    for record in history_records:
        try:
            ts = int(record.get("timestamp"))
            record["date_str"] = datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
        except:
            record["date_str"] = "Unknown"

    return render_template("user_history.html", user=user, history=history_records)



@app.route("/search/advanced/", methods=["GET", "POST"])
def advanced_search():
    results = []
    query_params = {}
    
    if request.method == "POST":
        category = request.form.get("category")
        keyword = request.form.get("keyword")
        date_start = request.form.get("date_start")
        
        query_filter = {}
        
        if category and category != "All":
            query_filter["category"] = category
            query_params["category"] = category

        if keyword:
            query_filter["title"] = {"$regex": keyword, "$options": "i"}
            query_params["keyword"] = keyword

        if date_start:
            try:
                dt_obj = datetime.strptime(date_start, "%Y-%m-%d")
                ts_ms = str(int(dt_obj.timestamp() * 1000))
                query_filter["timestamp"] = {"$gte": ts_ms}
                query_params["date_start"] = date_start
            except ValueError:
                pass

        results = list(articles_collection.find(query_filter).limit(20))
        
        for article in results:
            image_filename = article.get("image", "").split(",")[0]
            if image_filename:
                article["image_url"] = f"/files/{image_filename}"

            ts = int(article.get("timestamp", 0))
            if ts:
                article["date_display"] = datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d')

    return render_template("advanced_search.html", results=results, params=query_params)


@app.route("/monitor/")
def monitor_page():
    return render_template("monitor.html")

@app.route("/api/monitor/stats")
def get_monitor_stats():
    """
    API: 获取实时集群状态和分片分布数据
    """
    try:
        server_status = client.admin.command("serverStatus")
        
        ops = server_status.get('opcounters', {})
        mem = server_status.get('mem', {})
        conns = server_status.get('connections', {})
        
        shards_info = {}
        
        target_collections = ['articles', 'pop_ranks']
        
        for col_name in target_collections:
            try:
                stats = db.command("collStats", col_name)
                if stats.get('sharded'):
                    shards_info[col_name] = {}
                    for shard_name, shard_data in stats['shards'].items():
                        shards_info[col_name][shard_name] = shard_data.get('count', 0)
            except Exception:
                shards_info[col_name] = {"Error": 0}

        return jsonify({
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "opcounters": ops,
            "memory": {
                "resident": mem.get('resident', 0), # MB
                "virtual": mem.get('virtual', 0)
            },
            "connections": conns.get('current', 0),
            "distribution": shards_info
        })
        
    except Exception as e:
        print(f"Monitor Error: {e}")
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
