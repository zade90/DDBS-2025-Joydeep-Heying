#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne

DAY_MS = 24 * 60 * 60 * 1000


def parse_args():
    parser = argparse.ArgumentParser(
        description="Spread read timestamps across days and rebuild pop_ranks."
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27041",
        help="MongoDB URI for the mongos router.",
    )
    parser.add_argument("--db", default="readersDb", help="Target database name.")
    parser.add_argument(
        "--reads-per-day",
        type=int,
        default=10,
        help="How many reads to place in each day bucket.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help="Seconds between reads within a day (0 = auto spread).",
    )
    parser.add_argument(
        "--base-date",
        default="",
        help="Base date in YYYY-MM-DD (UTC). Empty = use min timestamp date.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Top N articles per snapshot.",
    )
    parser.add_argument(
        "--skip-rewrite",
        action="store_true",
        help="Skip rewriting read timestamps.",
    )
    return parser.parse_args()


def sort_key(doc):
    raw = str(doc.get("id", ""))
    if raw.startswith("r") and raw[1:].isdigit():
        return int(raw[1:])
    return raw or str(doc.get("_id"))


def coerce_ts(value):
    try:
        return int(value)
    except Exception:
        return None


def compute_base_ms(docs, base_date):
    if base_date:
        dt = datetime.strptime(base_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    min_ts = None
    for doc in docs:
        ts = coerce_ts(doc.get("timestamp"))
        if ts is None:
            continue
        if min_ts is None or ts < min_ts:
            min_ts = ts
    if min_ts is None:
        raise ValueError("No valid timestamps found in reads.")
    return (min_ts // DAY_MS) * DAY_MS


def rewrite_timestamps(reads, docs, reads_per_day, interval_ms, base_ms):
    ops = []
    for idx, doc in enumerate(sorted(docs, key=sort_key)):
        day_offset = idx // reads_per_day
        within = idx % reads_per_day
        ts_ms = base_ms + day_offset * DAY_MS + within * interval_ms
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"timestamp": str(ts_ms)}}))
    if ops:
        reads.bulk_write(ops, ordered=False)
    return len(ops)


def build_pipeline(granularity, date_fields, date_from_parts, id_prefix, top_n):
    base_project = {
        "$project": {
            "date": {"$toDate": {"$toLong": "$timestamp"}},
            "aid": 1,
            "agreeOrNot": {"$toInt": "$agreeOrNot"},
            "commentOrNot": {"$toInt": "$commentOrNot"},
            "shareOrNot": {"$toInt": "$shareOrNot"},
        }
    }
    pop_score = {"$add": [1, "$agreeOrNot", "$commentOrNot", "$shareOrNot"]}
    return [
        base_project,
        {"$addFields": {**date_fields, "popScore": pop_score}},
        {
            "$addFields": {
                "timestamp": {
                    "$subtract": [
                        {"$dateFromParts": date_from_parts},
                        datetime(1970, 1, 1, tzinfo=timezone.utc),
                    ]
                }
            }
        },
        {"$group": {"_id": {"timestamp": "$timestamp", "aid": "$aid"}, "popScoreAgg": {"$sum": "$popScore"}}},
        {"$sort": {"_id.timestamp": 1, "popScoreAgg": -1}},
        {"$group": {"_id": "$_id.timestamp", "articleAidList": {"$push": "$_id.aid"}}},
        {
            "$project": {
                "_id": {"$concat": [id_prefix, {"$toString": "$_id"}]},
                "timestamp": "$_id",
                "articleAidList": {"$slice": ["$articleAidList", top_n]},
                "temporalGranularity": granularity,
            }
        },
    ]


def rebuild_pop_ranks(db, top_n):
    reads = db["reads"]

    monthly = build_pipeline(
        "monthly",
        {"year": {"$year": "$date"}, "month": {"$month": "$date"}},
        {"year": "$year", "month": "$month"},
        "m",
        top_n,
    )
    weekly = build_pipeline(
        "weekly",
        {"year": {"$year": "$date"}, "month": {"$month": "$date"}, "week": {"$week": "$date"}},
        {"isoWeekYear": "$year", "isoWeek": "$week"},
        "w",
        top_n,
    )
    daily = build_pipeline(
        "daily",
        {"year": {"$year": "$date"}, "month": {"$month": "$date"}, "day": {"$dayOfYear": "$date"}},
        {"year": "$year", "month": "$month", "day": "$day"},
        "d",
        top_n,
    )

    monthly_docs = list(reads.aggregate(monthly, allowDiskUse=True))
    weekly_docs = list(reads.aggregate(weekly, allowDiskUse=True))
    daily_docs = list(reads.aggregate(daily, allowDiskUse=True))

    db["pop_ranks"].delete_many({})
    all_docs = monthly_docs + weekly_docs + daily_docs
    if all_docs:
        db["pop_ranks"].insert_many(all_docs)

    return {
        "monthly": len(monthly_docs),
        "weekly": len(weekly_docs),
        "daily": len(daily_docs),
    }


def main():
    args = parse_args()
    client = MongoClient(args.mongo_uri)
    db = client[args.db]
    reads = db["reads"]

    docs = list(reads.find({}, {"_id": 1, "id": 1, "timestamp": 1}))
    if not docs:
        raise SystemExit("No reads found. Did you load data?")

    if not args.skip_rewrite:
        base_ms = compute_base_ms(docs, args.base_date)
        if args.interval_seconds > 0:
            interval_ms = args.interval_seconds * 1000
        else:
            interval_ms = max(1, DAY_MS // args.reads_per_day)
        updated = rewrite_timestamps(reads, docs, args.reads_per_day, interval_ms, base_ms)
        print(f"Updated {updated} read timestamps.")

    counts = rebuild_pop_ranks(db, args.top_n)
    print(
        "Rebuilt pop_ranks snapshots:"
        f" daily={counts['daily']}, weekly={counts['weekly']}, monthly={counts['monthly']}"
    )


if __name__ == "__main__":
    main()
