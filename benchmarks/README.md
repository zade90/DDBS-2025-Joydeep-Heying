# Benchmarks

This folder contains a lightweight benchmark runner for the MongoDB sharded cluster.

## What it measures

- Data load duration (per step + per dataset summary)
- Query latency (cold + warm p50/p95/avg)
- Shard distribution (doc counts + sizes per shard)
- Chunk distribution and shard key/tag metadata
- Cluster health (serverStatus + replication lag)

## Prerequisites

- MongoDB sharded cluster is running via docker-compose.
- Data is loaded (unless you are running the load benchmark).
- Python environment has `pymongo` installed.

## Usage

Run everything (except load):

```bash
python benchmarks/run_benchmarks.py
```

Run only query latency tests:

```bash
python benchmarks/run_benchmarks.py --queries --iterations 50 --warmup 2
```

Run cache benchmark (requires the Flask app running on port 6510):

```bash
python benchmarks/run_benchmarks.py --cache --app-base-url http://localhost:6510
```

If Redis runs on a different host/port:

```bash
python benchmarks/run_benchmarks.py --cache --redis-url redis://localhost:6380/0 --app-base-url http://localhost:6510
```

Collect shard distribution and chunk stats:

```bash
python benchmarks/run_benchmarks.py --distribution
```

Collect cluster health and replication lag:

```bash
python benchmarks/run_benchmarks.py --health
```

Measure data load time (this will import data again):

```bash
python benchmarks/run_benchmarks.py --load
```

## Output

Reports are written to `reports/` (CSV + Markdown tables):

- `load_times.csv`, `load_times.md`
- `load_summary.csv`, `load_summary.md`
- `query_times.csv`, `query_times.md`
- `shard_distribution.csv`, `shard_distribution.md`
- `chunk_distribution.csv`, `chunk_distribution.md`
- `shard_keys.csv`, `shard_keys.md`
- `tag_ranges.csv`, `tag_ranges.md`
- `replication_status.csv`, `replication_status.md`
- `cluster_health.json`
- `cache_times.csv`, `cache_times.md`
- `cache_stats.csv`, `cache_stats.md`

## Notes on caching

The app now caches query results in Redis (between the app and database). Cache tests are
reported via `cache_times.*` and `cache_stats.*`. You can disable caching by setting
`CACHE_ENABLED=0` when starting the app.
