from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
from pydantic import BaseModel
import os
import subprocess
import threading
import time
import gridfs
from flask import Flask, render_template, send_file, Response
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from io import BytesIO
import redis

os.environ["FAST_REMOVE"] = "1"
client = MongoClient("mongodb://localhost:27041/")  
MEDIA_FILES_MONGO_URI = "mongodb://localhost:27041" 
media_client = MongoClient(MEDIA_FILES_MONGO_URI)
db = client["readersDb"] 
media_db = media_client["readersDb"]  
users_collection = db["users"] 
articles_collection = db["articles"] 
pop_ranks_collection = db["pop_ranks"]
reads_collection = db["reads"]
fs = gridfs.GridFS(media_db)
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'

ACTION_STATE = {}
ACTION_LOCK = threading.Lock()

def _update_action(name, payload):
    with ACTION_LOCK:
        ACTION_STATE[name] = {**ACTION_STATE.get(name, {}), **payload}

def _run_script_action(name, script_path, env=None):
    _update_action(name, {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "output": ""
    })
    try:
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_lines.append(line.rstrip())
                output_lines = output_lines[-200:]
                _update_action(name, {
                    "status": "running",
                    "output": "\n".join(output_lines)
                })
        return_code = process.wait()
        final_output = "\n".join(output_lines).strip()
        if return_code == 0:
            _update_action(name, {
                "status": "success",
                "finished_at": datetime.now().isoformat(),
                "output": final_output
            })
        else:
            _update_action(name, {
                "status": "error",
                "finished_at": datetime.now().isoformat(),
                "output": final_output or f"Exit code {return_code}"
            })
    except Exception as exc:
        _update_action(name, {
            "status": "error",
            "finished_at": datetime.now().isoformat(),
            "output": str(exc)
        })

def _start_action(name, script_path, env=None):
    with ACTION_LOCK:
        state = ACTION_STATE.get(name, {})
        if state.get("status") == "running":
            return False
    thread = threading.Thread(target=_run_script_action, args=(name, script_path, env), daemon=True)
    thread.start()
    return True


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
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 12
    total_users = users_collection.count_documents({})
    total_pages = max((total_users + per_page - 1) // per_page, 1)
    if page > total_pages:
        page = total_pages

    users = list(
        users_collection.find()
        .sort("timestamp", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    for user in users:
        user["_id"] = str(user["_id"])
    return render_template("users.html", users=users, page=page, total_pages=total_pages)


@app.route("/users/edit/<user_id>/", methods=["GET", "POST"])
def edit_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404

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

        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})

        return redirect(url_for('users_page'))

    return render_template("edit_user.html", user=user)

@app.route("/articles/")
def articles_page():
    search_query = request.args.get('search', '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 9
    query_filter = {}
    if search_query:
        query_filter["title"] = search_query

    total_articles = articles_collection.count_documents(query_filter)
    total_pages = max((total_articles + per_page - 1) // per_page, 1)
    if page > total_pages:
        page = total_pages

    articles = list(
        articles_collection.find(query_filter)
        .sort("timestamp", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    for article in articles:
        image_filename = article.get("image")
        image_filename = image_filename.split(",")[0] if image_filename else ""
        if image_filename:
            article["image_url"] = f"/files/{image_filename}"
        else:
            article["image_url"] = None

    return render_template(
        "articles.html",
        articles=articles,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )

def format_timestamp(timestamp_ms):
    timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)
    return timestamp.strftime('%B %d, %Y, %I:%M %p')

@app.route("/poprank/", methods=["GET", "POST"])
def poprank_page():
    if request.method == "POST":
        granularity = request.form.get("granularity")
        if granularity:
            poprank_data = list(pop_ranks_collection.find({"temporalGranularity": granularity}))
            
            all_articles = []
            for record in poprank_data:
                article_ids = record.get("articleAidList", [])
                articles = []
                for article_id in article_ids:
                    article_id_prefixed = f"a{article_id}"
                    article = articles_collection.find_one({"aid": article_id_prefixed})
                    if article:
                        articles.append(article)

                formatted_date = format_timestamp(record.get("timestamp"))

                all_articles.append({
                    "timestamp": formatted_date,
                    "articles": articles,
                    "timestamp_ms": record.get("timestamp")
                })
            
            return render_template("poprank_display.html", granularity=granularity, all_articles=all_articles)
    
    return render_template("poprank_select_granularity.html")

@app.route("/poprank/<granularity>/<timestamp>/")
def poprank_ranking(granularity, timestamp):
    timestamp_ms = int(timestamp)
    print(timestamp_ms)
    record = pop_ranks_collection.find_one({
        "temporalGranularity": granularity,
        "timestamp": timestamp_ms
    })
    print(record)
    if not record:
        return "PopRank record not found", 404
    
    article_ids = record.get("articleAidList", [])
    articles = []
    for article_id in article_ids:
        article_id_prefixed = f"a{article_id}"
        article = articles_collection.find_one({"id": article_id_prefixed})
        if article:
            articles.append(article)
    
    formatted_date = format_timestamp(record.get("timestamp"))

    return render_template("poprank_ranking.html", granularity=granularity, timestamp=formatted_date, articles=articles)

    return render_template("poprank_select_granularity.html")

@app.route("/users/add/", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
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
        
        user_id = f"u{str(int(datetime.utcnow().timestamp()))[-4:]}"
        timestamp = str(int(datetime.utcnow().timestamp() * 1000))
        uid = str(int(datetime.utcnow().timestamp() * 1000))
        
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

        users_collection.insert_one(user_data)

        return redirect(url_for('users_page'))

    return render_template("add_user.html")

@app.route("/users/delete/<user_id>/", methods=["GET"])
def delete_user(user_id):
    users_collection.delete_one({"_id": ObjectId(user_id)})
    return redirect(url_for('users_page'))

@app.route('/files/<filename>')
def serve_file(filename):
    file = media_db.fs.files.find_one({"filename": filename})
    
    if not file:
        return "File not found", 404
    
    file_id = file['_id']
    grid_out = fs.get(file_id)
    
    ext = filename.split('.')[-1].lower()
    content_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "flv": "video/x-flv",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")
    
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
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        text = request.files.get("text")
        text_filename = None
        if text and text.filename:
            text_filename = secure_filename(text.filename)
            text.save(os.path.join(app.config['UPLOAD_FOLDER'], text_filename))

        image = request.files.get("image")
        image_filename = ""
        if image and image.filename:
            safe_img_name = secure_filename(image.filename)
            fs.put(image, filename=safe_img_name, content_type=image.content_type)
            image_filename = safe_img_name

        video = request.files.get("video")
        video_filename = ""
        if video and video.filename:
            safe_vid_name = secure_filename(video.filename)
            fs.put(video, filename=safe_vid_name, content_type=video.content_type)
            video_filename = safe_vid_name

        article_data = {
            "title": title,
            "category": category,
            "abstract": abstract,
            "articleTags": article_tags,
            "authors": authors,
            "language": language,
            "timestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "text": text_filename,
            "image": image_filename, 
            "video": video_filename,
        }
        
        articles_collection.insert_one(article_data)
        return redirect(url_for('add_article', status='success'))

    status = request.args.get('status', '')
    return render_template("add_article.html", status=status)

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
        
        text = request.files.get("text")
        if text:
            text_filename = secure_filename(text.filename)
            text.save(os.path.join(app.config['UPLOAD_FOLDER'], text_filename))
        else:
            text_filename = article.get("text", None)
        
        existing_images = article.get("image", "")
        video_filename = article.get("video", None)

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
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    
    if not article:
        return "Article not found", 404

    articles_collection.delete_one({"_id": ObjectId(article_id)})

    return redirect(url_for('articles_page'))


@app.route("/articles/<article_id>/")
def article_detail(article_id):
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    if not article:
        return "Article not found", 404
    
    article["_id"] = str(article["_id"])

    timestamp_ms = int(article.get("timestamp", 0))
    if timestamp_ms:
        timestamp = datetime.utcfromtimestamp(timestamp_ms / 1000)
        article["human_readable_timestamp"] = timestamp.strftime('%B %d, %Y, %I:%M %p')
    else:
        article["human_readable_timestamp"] = "Date not available"
    
    image_filenames_list = article.get("image", "").split(",")[0:-1]
    image_urls = []
    
    for image_filename in image_filenames_list:
        if image_filename:
            image_file = fs.find_one({"filename": image_filename})
            if image_file:
                image_urls.append(f"/files/{image_filename}")
            else:
                image_urls.append(None)
        else:
            image_urls.append(None)
    
    article["image_urls"] = image_urls

    text_filename = article.get("text")
    if text_filename:
        text_file = fs.find_one({"filename": text_filename})
        if text_file:
            article["content"] = text_file.read().decode('utf-8')
        else:
            article["content"] = "Content not found."
    else:
        article["content"] = "No text content available."

    video_filename = article.get("video")
    if video_filename:
        video_file = fs.find_one({"filename": video_filename})
        if video_file:
            article["video_url"] = f"/files/{video_filename}"
        else:
            article["video_url"] = None
    else:
        article["video_url"] = None

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
    try:
        server_status = client.admin.command("serverStatus")
        
        ops = server_status.get('opcounters', {})
        mem = server_status.get('mem', {})
        conns = server_status.get('connections', {})
        
        shards = []
        shard_ids = []
        try:
            config_shards = list(client["config"]["shards"].find({}, {"_id": 1, "host": 1}))
            for shard in config_shards:
                shard_id = shard.get("_id")
                shards.append({
                    "id": shard_id,
                    "host": shard.get("host", "")
                })
                if shard_id:
                    shard_ids.append(shard_id)
        except Exception:
            try:
                list_shards = client.admin.command("listShards")
                for shard in list_shards.get("shards", []):
                    shard_id = shard.get("_id")
                    shards.append({
                        "id": shard_id,
                        "host": shard.get("host", "")
                    })
                    if shard_id:
                        shard_ids.append(shard_id)
            except Exception:
                pass

        shards_info = {}
        
        target_collections = ['articles', 'pop_ranks']
        
        for col_name in target_collections:
            try:
                stats = db.command("collStats", col_name)
                if stats.get('sharded'):
                    shards_info[col_name] = {}
                    for shard_id in shard_ids:
                        shards_info[col_name][shard_id] = 0
                    for shard_name, shard_data in stats['shards'].items():
                        shards_info[col_name][shard_name] = shard_data.get('count', 0)
            except Exception:
                shards_info[col_name] = {"Error": 0}

        return jsonify({
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "opcounters": ops,
            "memory": {
                "resident": mem.get('resident', 0),
                "virtual": mem.get('virtual', 0)
            },
            "connections": conns.get('current', 0),
            "shards": shards,
            "distribution": shards_info
        })
        
    except Exception as e:
        print(f"Monitor Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/monitor/action/<action_name>", methods=["GET"])
def get_action_status(action_name):
    with ACTION_LOCK:
        state = ACTION_STATE.get(action_name, {"status": "idle"})
    return jsonify(state)

@app.route("/api/monitor/action/<action_name>/start", methods=["POST"])
def start_action(action_name):
    scripts = {
        "add_shard3": os.path.join(os.getcwd(), "shard3_add.sh"),
        "migrate_shard3": os.path.join(os.getcwd(), "shard3_migrate_chunks.sh"),
        "remove_shard3": os.path.join(os.getcwd(), "shard3_remove.sh")
    }
    script_path = scripts.get(action_name)
    if not script_path or not os.path.exists(script_path):
        return jsonify({"error": "Unknown action"}), 404
    payload = request.get_json(silent=True) or {}
    env = None
    if action_name == "add_shard3" and payload.get("reset"):
        env = os.environ.copy()
        env["RESET_SHARD3"] = "1"
    started = _start_action(action_name, script_path, env=env)
    return jsonify({"started": started, "action": action_name})
    
if __name__ == "__main__":
    # app.run(debug=True)
    app.run(port=6510, debug=True)
