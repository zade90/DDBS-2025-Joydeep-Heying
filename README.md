# Mocking Distributed Databases - System Manual

This document is the system manual and operating specification. It covers installation,
configuration, and operation of the system and is intended to be delivered alongside the
system executable program (`main.py`).

## Overview

This project runs a sharded MongoDB cluster using Docker and exposes a Flask-based web UI
for monitoring shard status, data distribution, and shard3 lifecycle actions.

## Prerequisites

- Linux host (or WSL)
- Docker Engine and Docker Compose plugin
- Python 3.x and pip

## Installation

1) Install Python dependencies:

```bash
pip install -r requirements.txt
```

2) Ensure the data files exist under `db-generation/` (this directory must not be modified):

- `db-generation/user.dat`
- `db-generation/article.dat`
- `db-generation/read.dat`
- `db-generation/articles/` (media assets)

## Configuration

- `setup_mongo_cluster.sh` auto-detects `HOSTIP` via `hostname -I`.
- Docker volumes are stored under `./data/`.
- MongoDB router is exposed on `localhost:27041`.
- Redis is started on `localhost:6379` (override with `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB`). If your host uses restrictive `docker-default` profiles, run Redis with `--security-opt apparmor=unconfined` (already set in `setup_mongo_cluster.sh`).
- Query cache settings (used by the Flask app): `CACHE_ENABLED=1`, `CACHE_TTL_SECONDS=300`, `CACHE_TTL_SHORT_SECONDS=60`.

If your host IP is different or you run multiple stacks, update `setup_mongo_cluster.sh` or
export `HOSTIP` before running it:

```bash
export HOSTIP=<your-host-ip>
```

## Operation

### 1) Start the MongoDB cluster

```bash
chmod +x setup_mongo_cluster.sh
./setup_mongo_cluster.sh
```

### 2) Load data into MongoDB

```bash
chmod +x load_mongodb_data.sh
./load_mongodb_data.sh
```

### 3) Upload media assets to GridFS

```bash
python upload_media_files.py
```

### 4) Optional background watchers

These scripts watch change streams and update derived collections in real time:

```bash
python watch_article_updates.py
python watch_read_updates.py
```

### 5) Start the system executable program (web UI)

```bash
python main.py
```

## Benchmarking

Benchmark scripts are provided under `benchmarks/` to measure load time, query latency,
shard distribution, and cluster health. See `benchmarks/README.md` for usage.

Open the UI at:

```
http://localhost:6510
```

## Services

- `monitor_service.py`: Background utilities and logic used by the monitor endpoints to collect shard registry and distribution data.
- `query_service.py`: Query helpers for read/history-related endpoints used by the web UI.

Both modules are imported by the system executable (`main.py`) and are not run as standalone servers.

## Frontend Structure

- Templates live in `templates/` and render the main pages: `monitor.html`, `articles.html`, `users.html`, `add_article.html`.
- Styling and client-side behavior are defined in `static/styles.css`.
- The monitor page calls `/api/monitor/*` endpoints for shard registry, distribution, and shard3 actions.

## Shard3 Operations

The UI exposes the following actions, which call the scripts below:

- Add shard3: `shard3_add.sh`
- Migrate chunks to shard3: `shard3_migrate_chunks.sh`
- Remove shard3: `shard3_remove.sh`

These scripts can also be run directly if needed.

## Notes

- `setup_mongo_cluster.sh` stops and removes all running containers and deletes `./data`.
  Only run it when you want a fresh cluster.
- If data load is repeated, ensure collections are in a clean state.
- Change-stream watchers will not print output unless new inserts occur.

## Troubleshooting

- If `load_mongodb_data.sh` fails, confirm the `db-generation/*.dat` files exist.
- If the UI shows no shard data, verify the MongoDB router is running on `localhost:27041`.
- If shard3 add/remove fails, check the corresponding script output in the UI action logs.
