#!/usr/bin/env python3
import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime

from pymongo import MongoClient
from bson import json_util
from pymongo.errors import PyMongoError

DEFAULT_MONGO_URI = "mongodb://localhost:27041"
DEFAULT_DB_NAME = "readersDb"
DEFAULT_OUTPUT_DIR = "reports"
DEFAULT_CONTAINER = "mongos_router"
DEFAULT_TMP_DIR = "/tmp/mdb_seed"
DEFAULT_APP_BASE_URL = "http://localhost:6510"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
CACHE_PREFIX = "cache:v1"
CACHE_STATS_KEY = f"{CACHE_PREFIX}:stats"
CACHE_VERSION_PREFIX = f"{CACHE_PREFIX}:version"

REPLICA_SETS = {
    "configReplSet": ["localhost:27019", "localhost:27020", "localhost:27021"],
    "shard1ReplSet": ["localhost:27031", "localhost:27032"],
    "shard2ReplSet": ["localhost:27033", "localhost:27034"],
    "shard3ReplSet": ["localhost:27035", "localhost:27036"],
}


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def write_markdown_table(path, headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def run_cmd(cmd, check=True, stdin_path=None):
    if stdin_path:
        with open(stdin_path, "rb") as handle:
            return subprocess.run(cmd, stdin=handle, check=check)
    return subprocess.run(cmd, check=check)


def timed_step(name, func, results):
    start = time.perf_counter()
    func()
    end = time.perf_counter()
    duration_ms = (end - start) * 1000
    results.append((name, round(duration_ms, 2)))


def run_load_benchmark(root_dir, output_dir, container, db_name):
    data_dir = os.path.join(root_dir, "db-generation")
    loaders_dir = os.path.join(root_dir, "shard_loaders")

    steps = []

    def docker_exec(args, stdin_path=None):
        cmd = ["docker", "exec", "-i", container] + args
        run_cmd(cmd, stdin_path=stdin_path)

    def docker_cp(src, dst):
        run_cmd(["docker", "cp", src, f"{container}:{dst}"])

    timed_step(
        "prepare_tmp_dir",
        lambda: docker_exec(["mkdir", "-p", DEFAULT_TMP_DIR]),
        steps,
    )

    for filename in ["user.dat", "article.dat", "read.dat"]:
        src_path = os.path.join(data_dir, filename)
        timed_step(
            f"copy_{filename}",
            lambda src=src_path, dst=filename: docker_cp(src, f"{DEFAULT_TMP_DIR}/{dst}"),
            steps,
        )

    config_scripts = [
        "configure_users_sharding.js",
        "configure_articles_sharding.js",
    ]
    for script in config_scripts:
        script_path = os.path.join(loaders_dir, script)
        timed_step(
            f"run_{script}",
            lambda sp=script_path: docker_exec(["mongosh", "--quiet"], stdin_path=sp),
            steps,
        )

    timed_step(
        "import_users",
        lambda: docker_exec([
            "mongoimport",
            "--db",
            db_name,
            "--collection",
            "users",
            "--file",
            f"{DEFAULT_TMP_DIR}/user.dat",
        ]),
        steps,
    )

    timed_step(
        "import_articles",
        lambda: docker_exec([
            "mongoimport",
            "--db",
            db_name,
            "--collection",
            "articles",
            "--file",
            f"{DEFAULT_TMP_DIR}/article.dat",
        ]),
        steps,
    )

    timed_step(
        "build_science_articles",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "build_science_articles.js")),
        steps,
    )

    timed_step(
        "configure_science_articles_sharding",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "configure_science_articles_sharding.js")),
        steps,
    )

    timed_step(
        "import_reads_unsharded",
        lambda: docker_exec([
            "mongoimport",
            "--db",
            db_name,
            "--collection",
            "reads_unsharded",
            "--file",
            f"{DEFAULT_TMP_DIR}/read.dat",
        ]),
        steps,
    )

    timed_step(
        "build_reads_unsharded",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "build_reads_unsharded.js")),
        steps,
    )

    timed_step(
        "build_bereads_unsharded",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "build_bereads_unsharded.js")),
        steps,
    )

    timed_step(
        "build_pop_ranks_unsharded",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "build_pop_ranks_unsharded.js")),
        steps,
    )

    timed_step(
        "build_science_bereads",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "build_science_bereads.js")),
        steps,
    )

    config_scripts = [
        "configure_reads_sharding.js",
        "configure_bereads_sharding.js",
        "configure_pop_ranks_sharding.js",
        "configure_science_bereads_sharding.js",
    ]
    for script in config_scripts:
        script_path = os.path.join(loaders_dir, script)
        timed_step(
            f"run_{script}",
            lambda sp=script_path: docker_exec(["mongosh", "--quiet"], stdin_path=sp),
            steps,
        )

    def export_import(source_collection, target_collection):
        export_path = f"{DEFAULT_TMP_DIR}/{source_collection}.json"
        docker_exec([
            "mongoexport",
            "--db",
            db_name,
            "--collection",
            source_collection,
            "--out",
            export_path,
        ])
        docker_exec([
            "mongoimport",
            "--db",
            db_name,
            "--collection",
            target_collection,
            "--file",
            export_path,
        ])

    timed_step(
        "export_import_reads",
        lambda: export_import("reads_unsharded", "reads"),
        steps,
    )
    timed_step(
        "export_import_bereads",
        lambda: export_import("bereads_unsharded", "bereads"),
        steps,
    )
    timed_step(
        "export_import_pop_ranks",
        lambda: export_import("pop_ranks_unsharded", "pop_ranks"),
        steps,
    )

    timed_step(
        "drop_temp_collections",
        lambda: docker_exec(["mongosh", "--quiet"], stdin_path=os.path.join(loaders_dir, "drop_temp_collections.js")),
        steps,
    )

    load_csv = os.path.join(output_dir, "load_times.csv")
    load_md = os.path.join(output_dir, "load_times.md")
    write_csv(load_csv, ["step", "duration_ms"], steps)
    write_markdown_table(load_md, ["step", "duration_ms"], steps)

    summary_rows = []
    dataset_map = {
        "users": ["import_users"],
        "articles": ["import_articles"],
        "reads": ["import_reads_unsharded", "export_import_reads"],
        "bereads": ["build_bereads_unsharded", "export_import_bereads"],
        "pop_ranks": ["build_pop_ranks_unsharded", "export_import_pop_ranks"],
        "sci_articles": ["build_science_articles"],
        "sci_bereads": ["build_science_bereads"],
    }
    step_times = dict(steps)
    for name, step_list in dataset_map.items():
        total = sum(step_times.get(step, 0) for step in step_list)
        summary_rows.append((name, round(total, 2)))
    summary_csv = os.path.join(output_dir, "load_summary.csv")
    summary_md = os.path.join(output_dir, "load_summary.md")
    write_csv(summary_csv, ["dataset", "duration_ms"], summary_rows)
    write_markdown_table(summary_md, ["dataset", "duration_ms"], summary_rows)

    return {
        "steps": steps,
        "summary": summary_rows,
    }


def sample_one(db, collection, projection=None):
    try:
        sample = list(db[collection].aggregate([
            {"$sample": {"size": 1}},
            {"$project": projection} if projection else {"$project": {"_id": 1}},
        ]))
        if sample:
            return sample[0]
    except PyMongoError:
        pass
    return db[collection].find_one({}, projection)


def run_query_benchmark(client, db_name, output_dir, iterations, warmup):
    db = client[db_name]

    samples = {
        "articles": sample_one(db, "articles", {"category": 1, "aid": 1, "title": 1}),
        "users": sample_one(db, "users", {"region": 1, "uid": 1}),
        "reads": sample_one(db, "reads", {"region": 1, "id": 1, "uid": 1}),
        "bereads": sample_one(db, "bereads", {"category": 1, "aid": 1}),
        "pop_ranks": sample_one(db, "pop_ranks", {"temporalGranularity": 1, "_id": 1}),
    }

    def safe_sample(name):
        doc = samples.get(name)
        if not doc:
            raise RuntimeError(f"Missing sample for {name}; ensure data is loaded.")
        return doc

    queries = []

    def find_one(collection, filter_doc, projection=None):
        return db[collection].find_one(filter_doc, projection)

    def find_many(collection, filter_doc, projection=None, limit=20):
        cursor = db[collection].find(filter_doc, projection).limit(limit)
        return list(cursor)

    def aggregate(collection, pipeline):
        return list(db[collection].aggregate(pipeline))

    art = safe_sample("articles")
    queries.append({
        "name": "articles_targeted_by_category_aid",
        "targeted": True,
        "execute": lambda: find_one("articles", {"category": art.get("category"), "aid": art.get("aid")}),
    })
    queries.append({
        "name": "articles_scatter_by_title",
        "targeted": False,
        "execute": lambda: find_one("articles", {"title": art.get("title")}),
    })

    usr = safe_sample("users")
    queries.append({
        "name": "users_targeted_by_region_uid",
        "targeted": True,
        "execute": lambda: find_one("users", {"region": usr.get("region"), "uid": usr.get("uid")}),
    })

    rd = safe_sample("reads")
    queries.append({
        "name": "reads_targeted_by_region_id",
        "targeted": True,
        "execute": lambda: find_many("reads", {"region": rd.get("region"), "id": rd.get("id")}, limit=10),
    })
    queries.append({
        "name": "reads_scatter_by_uid",
        "targeted": False,
        "execute": lambda: find_many("reads", {"uid": rd.get("uid")}, limit=20),
    })

    br = safe_sample("bereads")
    queries.append({
        "name": "bereads_targeted_by_category_aid",
        "targeted": True,
        "execute": lambda: find_one("bereads", {"category": br.get("category"), "aid": br.get("aid")}),
    })

    pr = safe_sample("pop_ranks")
    queries.append({
        "name": "pop_ranks_targeted_by_granularity_id",
        "targeted": True,
        "execute": lambda: find_one("pop_ranks", {"temporalGranularity": pr.get("temporalGranularity"), "_id": pr.get("_id")}),
    })

    queries.append({
        "name": "user_history_pipeline",
        "targeted": False,
        "execute": lambda: aggregate("reads", [
            {"$match": {"uid": usr.get("uid")}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 10},
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "aid",
                    "foreignField": "aid",
                    "as": "article_details",
                }
            },
            {"$unwind": "$article_details"},
            {
                "$project": {
                    "uid": 1,
                    "timestamp": 1,
                    "aid": 1,
                    "title": "$article_details.title",
                    "category": "$article_details.category",
                }
            },
        ]),
    })

    results = []

    for query in queries:
        cold_start = time.perf_counter()
        query["execute"]()
        cold_ms = (time.perf_counter() - cold_start) * 1000

        for _ in range(warmup):
            query["execute"]()

        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            query["execute"]()
            timings.append((time.perf_counter() - start) * 1000)

        timings.sort()
        p50 = statistics.median(timings)
        p95 = timings[int(len(timings) * 0.95) - 1]
        avg = sum(timings) / len(timings)

        results.append((
            query["name"],
            "targeted" if query["targeted"] else "scatter",
            round(cold_ms, 2),
            round(p50, 2),
            round(p95, 2),
            round(avg, 2),
            iterations,
        ))

    query_csv = os.path.join(output_dir, "query_times.csv")
    query_md = os.path.join(output_dir, "query_times.md")
    headers = ["query", "type", "cold_ms", "p50_ms", "p95_ms", "avg_ms", "iterations"]
    write_csv(query_csv, headers, results)
    write_markdown_table(query_md, headers, results)

    return results


def run_cache_benchmark(client, db_name, output_dir, base_url, redis_url):
    httpx = None
    try:
        import httpx as httpx_module
        httpx = httpx_module
    except ImportError:
        httpx = None

    try:
        import redis
    except ImportError:
        print("[cache] redis client is not available; skipping cache benchmark.")
        return None

    db = client[db_name]
    sample_article = sample_one(db, "articles", {"_id": 1, "aid": 1})
    sample_user = sample_one(db, "users", {"uid": 1})
    if not sample_article or not sample_user:
        print("[cache] Missing sample data; ensure data is loaded.")
        return None

    article_id = str(sample_article.get("_id") or sample_article.get("aid") or "")
    uid = str(sample_user.get("uid") or "")
    if not article_id or not uid:
        print("[cache] Missing sample identifiers; skipping cache benchmark.")
        return None

    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    try:
        redis_client.delete(CACHE_STATS_KEY)
        for resource in ["articles", "users", "reads", "poprank"]:
            redis_client.incr(f"{CACHE_VERSION_PREFIX}:{resource}")
    except redis.exceptions.RedisError:
        print("[cache] Redis unavailable; skipping cache benchmark.")
        return None

    base_url = base_url.rstrip("/")
    endpoints = [
        ("articles_list", "GET", "/articles/"),
        ("users_list", "GET", "/users/"),
        ("article_detail", "GET", f"/articles/{article_id}/"),
        ("user_history", "GET", f"/users/{uid}/history/"),
        ("poprank_daily", "POST", "/poprank/", {"granularity": "daily"}),
    ]

    def read_stats():
        stats = redis_client.hgetall(CACHE_STATS_KEY) or {}
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        return hits, misses

    def request_endpoint_httpx(httpx_client, method, path, data=None):
        start = time.perf_counter()
        if method == "GET":
            response = httpx_client.get(path)
        else:
            response = httpx_client.post(path, data=data)
        duration_ms = (time.perf_counter() - start) * 1000
        return response.status_code, round(duration_ms, 2)

    def request_endpoint_urllib(method, path, data=None):
        import urllib.error
        import urllib.parse
        import urllib.request

        url = f"{base_url}{path}"
        encoded = None
        headers = {}
        if method == "POST":
            encoded = urllib.parse.urlencode(data or {}).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(url, data=encoded, headers=headers)
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=10.0) as response:
                response.read()
                status_code = response.getcode()
        except urllib.error.HTTPError as exc:
            exc.read()
            status_code = exc.code
        duration_ms = (time.perf_counter() - start) * 1000
        return status_code, round(duration_ms, 2)

    results = []
    if httpx:
        try:
            with httpx.Client(base_url=base_url, timeout=10.0, follow_redirects=True) as httpx_client:
                for name, method, path, *rest in endpoints:
                    payload = rest[0] if rest else None

                    hits_before, misses_before = read_stats()
                    status_cold, cold_ms = request_endpoint_httpx(httpx_client, method, path, payload)
                    hits_after, misses_after = read_stats()
                    cold_hits = hits_after - hits_before
                    cold_misses = misses_after - misses_before

                    hits_before, misses_before = read_stats()
                    status_warm, warm_ms = request_endpoint_httpx(httpx_client, method, path, payload)
                    hits_after, misses_after = read_stats()
                    warm_hits = hits_after - hits_before
                    warm_misses = misses_after - misses_before

                    results.append((
                        name,
                        method,
                        path,
                        status_cold,
                        status_warm,
                        cold_ms,
                        warm_ms,
                        cold_hits,
                        cold_misses,
                        warm_hits,
                        warm_misses,
                    ))
        except httpx.RequestError as exc:
            print(f"[cache] HTTP error: {exc}. Ensure the app is running at {base_url}.")
            return None
    else:
        try:
            for name, method, path, *rest in endpoints:
                payload = rest[0] if rest else None

                hits_before, misses_before = read_stats()
                status_cold, cold_ms = request_endpoint_urllib(method, path, payload)
                hits_after, misses_after = read_stats()
                cold_hits = hits_after - hits_before
                cold_misses = misses_after - misses_before

                hits_before, misses_before = read_stats()
                status_warm, warm_ms = request_endpoint_urllib(method, path, payload)
                hits_after, misses_after = read_stats()
                warm_hits = hits_after - hits_before
                warm_misses = misses_after - misses_before

                results.append((
                    name,
                    method,
                    path,
                    status_cold,
                    status_warm,
                    cold_ms,
                    warm_ms,
                    cold_hits,
                    cold_misses,
                    warm_hits,
                    warm_misses,
                ))
        except Exception as exc:
            print(f"[cache] HTTP error: {exc}. Ensure the app is running at {base_url}.")
            return None

    headers = [
        "endpoint",
        "method",
        "path",
        "status_cold",
        "status_warm",
        "cold_ms",
        "warm_ms",
        "cold_hits",
        "cold_misses",
        "warm_hits",
        "warm_misses",
    ]
    cache_csv = os.path.join(output_dir, "cache_times.csv")
    cache_md = os.path.join(output_dir, "cache_times.md")
    write_csv(cache_csv, headers, results)
    write_markdown_table(cache_md, headers, results)

    stats = redis_client.hgetall(CACHE_STATS_KEY) or {}
    stats_rows = [(key, value) for key, value in stats.items()]
    stats_csv = os.path.join(output_dir, "cache_stats.csv")
    stats_md = os.path.join(output_dir, "cache_stats.md")
    write_csv(stats_csv, ["metric", "value"], stats_rows)
    write_markdown_table(stats_md, ["metric", "value"], stats_rows)

    return results


def run_distribution_report(client, db_name, output_dir):
    db = client[db_name]
    collections = [
        "users",
        "articles",
        "reads",
        "bereads",
        "pop_ranks",
        "sci_articles",
        "sci_bereads",
    ]

    distribution_rows = []
    for collection in collections:
        try:
            stats = db.command("collStats", collection)
        except PyMongoError:
            distribution_rows.append((collection, "error", 0, 0, 0))
            continue
        if not stats.get("sharded"):
            distribution_rows.append((collection, "not_sharded", stats.get("count", 0), 0, 0))
            continue
        for shard_name, shard_data in stats.get("shards", {}).items():
            count = shard_data.get("count", 0)
            size_mb = round(shard_data.get("size", 0) / (1024 * 1024), 2)
            storage_mb = round(shard_data.get("storageSize", 0) / (1024 * 1024), 2)
            distribution_rows.append((collection, shard_name, count, size_mb, storage_mb))

    dist_csv = os.path.join(output_dir, "shard_distribution.csv")
    dist_md = os.path.join(output_dir, "shard_distribution.md")
    headers = ["collection", "shard", "doc_count", "data_mb", "storage_mb"]
    write_csv(dist_csv, headers, distribution_rows)
    write_markdown_table(dist_md, headers, distribution_rows)

    def chunk_counts_for_namespace(namespace):
        try:
            chunks = list(client.config.chunks.aggregate([
                {"$match": {"ns": namespace}},
                {"$group": {"_id": "$shard", "count": {"$sum": 1}}},
            ]))
        except PyMongoError:
            return []
        if chunks:
            return chunks
        try:
            coll = client.config.collections.find_one({"_id": namespace}, {"uuid": 1})
        except PyMongoError:
            return []
        if not coll or "uuid" not in coll:
            return []
        try:
            return list(client.config.chunks.aggregate([
                {"$match": {"uuid": coll["uuid"]}},
                {"$group": {"_id": "$shard", "count": {"$sum": 1}}},
            ]))
        except PyMongoError:
            return []

    chunk_rows = []
    for collection in collections:
        ns = f"{db_name}.{collection}"
        chunks = chunk_counts_for_namespace(ns)
        if not chunks:
            chunk_rows.append((collection, "not_sharded_or_no_chunks", 0))
            continue
        for chunk in chunks:
            chunk_rows.append((collection, chunk.get("_id"), chunk.get("count", 0)))

    chunk_csv = os.path.join(output_dir, "chunk_distribution.csv")
    chunk_md = os.path.join(output_dir, "chunk_distribution.md")
    write_csv(chunk_csv, ["collection", "shard", "chunks"], chunk_rows)
    write_markdown_table(chunk_md, ["collection", "shard", "chunks"], chunk_rows)

    shard_key_rows = []
    try:
        for entry in client.config.collections.find({"_id": {"$regex": f"^{db_name}\\."}}):
            shard_key_rows.append((entry.get("_id"), json_util.dumps(entry.get("key", {}))))
    except PyMongoError:
        pass

    shard_key_csv = os.path.join(output_dir, "shard_keys.csv")
    shard_key_md = os.path.join(output_dir, "shard_keys.md")
    write_csv(shard_key_csv, ["namespace", "shard_key"], shard_key_rows)
    write_markdown_table(shard_key_md, ["namespace", "shard_key"], shard_key_rows)

    tag_rows = []
    try:
        for entry in client.config.tags.find({"ns": {"$regex": f"^{db_name}\\."}}):
            tag_rows.append((
                entry.get("ns"),
                entry.get("tag"),
                json_util.dumps(entry.get("min", {})),
                json_util.dumps(entry.get("max", {})),
            ))
    except PyMongoError:
        pass

    tag_csv = os.path.join(output_dir, "tag_ranges.csv")
    tag_md = os.path.join(output_dir, "tag_ranges.md")
    write_csv(tag_csv, ["namespace", "tag", "min", "max"], tag_rows)
    write_markdown_table(tag_md, ["namespace", "tag", "min", "max"], tag_rows)

    return {
        "distribution": distribution_rows,
        "chunks": chunk_rows,
        "shard_keys": shard_key_rows,
        "tags": tag_rows,
    }


def run_cluster_health(client, output_dir):
    health = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    try:
        status = client.admin.command("serverStatus")
        health["opcounters"] = status.get("opcounters", {})
        health["connections"] = status.get("connections", {})
        health["mem"] = status.get("mem", {})
        health["uptime"] = status.get("uptime", 0)
    except PyMongoError as exc:
        health["serverStatusError"] = str(exc)

    try:
        shards = list(client.admin.command("listShards").get("shards", []))
        health["shards"] = shards
    except PyMongoError as exc:
        health["listShardsError"] = str(exc)

    repl_rows = []
    for replset, hosts in REPLICA_SETS.items():
        status = None
        for host in hosts:
            try:
                local_client = MongoClient(host, serverSelectionTimeoutMS=2000)
                status = local_client.admin.command("replSetGetStatus")
                break
            except PyMongoError:
                continue
        if not status:
            continue

        primary_time = None
        for member in status.get("members", []):
            if member.get("stateStr") == "PRIMARY":
                primary_time = member.get("optimeDate")
                break

        for member in status.get("members", []):
            lag_sec = None
            if primary_time and member.get("optimeDate"):
                lag_sec = (primary_time - member.get("optimeDate")).total_seconds()
            repl_rows.append((
                replset,
                member.get("name"),
                member.get("stateStr"),
                member.get("health"),
                member.get("optimeDate"),
                lag_sec,
            ))

    repl_csv = os.path.join(output_dir, "replication_status.csv")
    repl_md = os.path.join(output_dir, "replication_status.md")
    repl_headers = ["replica_set", "member", "state", "health", "optime", "lag_sec"]
    write_csv(repl_csv, repl_headers, repl_rows)
    write_markdown_table(repl_md, repl_headers, repl_rows)

    health_path = os.path.join(output_dir, "cluster_health.json")
    with open(health_path, "w", encoding="utf-8") as handle:
        json.dump(health, handle, indent=2, default=str)

    return {
        "health": health,
        "replication": repl_rows,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark MongoDB sharded cluster performance.")
    parser.add_argument("--mongo-uri", default=DEFAULT_MONGO_URI)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--load", action="store_true", help="Run data load benchmark (destructive if data already exists).")
    parser.add_argument("--queries", action="store_true", help="Run query latency benchmark.")
    parser.add_argument("--distribution", action="store_true", help="Collect shard distribution and chunk stats.")
    parser.add_argument("--health", action="store_true", help="Collect cluster health and replication status.")
    parser.add_argument("--cache", action="store_true", help="Run cache benchmark against the running app.")
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument("--redis-url", default=DEFAULT_REDIS_URL)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_dir(args.output_dir)

    run_all = not (args.load or args.queries or args.distribution or args.health or args.cache)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.load or run_all:
        print("[load] Running data load benchmark...", flush=True)
        run_load_benchmark(root_dir, args.output_dir, DEFAULT_CONTAINER, args.db_name)

    client = MongoClient(args.mongo_uri)

    if args.queries or run_all:
        print("[queries] Running query latency benchmark...", flush=True)
        run_query_benchmark(client, args.db_name, args.output_dir, args.iterations, args.warmup)

    if args.distribution or run_all:
        print("[distribution] Collecting shard distribution...", flush=True)
        run_distribution_report(client, args.db_name, args.output_dir)

    if args.health or run_all:
        print("[health] Collecting cluster health...", flush=True)
        run_cluster_health(client, args.output_dir)

    if args.cache:
        print("[cache] Running cache benchmark...", flush=True)
        run_cache_benchmark(client, args.db_name, args.output_dir, args.app_base_url, args.redis_url)

    print(f"Reports written to {args.output_dir}")


if __name__ == "__main__":
    sys.exit(main())
