from datetime import datetime

import numpy as np
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27041"
DB_NAME = "readersDb"


def timestamp_to_datetime(raw_ts):
    return datetime.fromtimestamp(int(str(raw_ts)[:-3]))


def update_bereads(db, change_doc):
    doc = db.bereads.find_one({"_id": change_doc["aid"]})
    doc["readOrNot"] = 1

    read_num = int(doc["readNum"]) + 1
    read_uid_list = list(doc["readUidList"])
    if int(change_doc["readOrNot"]) > 0 and (change_doc["uid"] not in read_uid_list):
        read_uid_list.append(change_doc["uid"])

    comment_num = int(doc["commentNum"]) + int(change_doc["commentOrNot"])
    comment_uid_list = list(doc["commentUidList"])
    if int(change_doc["commentOrNot"]) > 0 and (change_doc["uid"] not in comment_uid_list):
        comment_uid_list.append(change_doc["uid"])

    agree_num = int(doc["agreeNum"]) + int(change_doc["agreeOrNot"])
    agree_uid_list = list(doc["agreeUidList"])
    if int(change_doc["agreeOrNot"]) > 0 and (change_doc["agreeOrNot"] not in agree_uid_list):
        agree_uid_list.append(change_doc["uid"])

    share_num = int(doc["shareNum"]) + int(change_doc["shareOrNot"])
    share_uid_list = list(doc["shareUidList"])
    if int(change_doc["shareOrNot"]) > 0 and (change_doc["uid"] not in share_uid_list):
        share_uid_list.append(str(change_doc["uid"]))

    payload = {
        "_id": doc["_id"],
        "category": doc["category"],
        "timestamp": doc["timestamp"],
        "readNum": read_num,
        "readUidList": read_uid_list,
        "commentNum": comment_num,
        "commentUidList": comment_uid_list,
        "agreeNum": agree_num,
        "agreeUidList": agree_uid_list,
        "shareNum": share_num,
        "shareUidList": share_uid_list,
        "aid": doc["aid"],
    }

    db.bereads.replace_one({"_id": change_doc["aid"]}, payload)
    print("db.bereads updated: ", payload)

    if change_doc["category"] == "science":
        db.sci_bereads.replace_one({"_id": change_doc["aid"]}, payload)
        print("db.sci_bereads also updated")


def month_cursor(db, month_value, year_value):
    return db.reads.find({
        "$and": [
            {
                "$expr": {
                    "$eq": [
                        {"$month": {"$toDate": {"$toLong": "$timestamp"}}},
                        month_value,
                    ]
                }
            },
            {
                "$expr": {
                    "$eq": [
                        {"$year": {"$toDate": {"$toLong": "$timestamp"}}},
                        year_value,
                    ]
                }
            },
        ]
    })


def top5_from_scores(score_map):
    scores = np.array(sorted(score_map.items(), key=lambda item: item[1], reverse=True))
    return list(scores[:5, 0])


def update_pop_ranks(db, change_doc):
    dt_change = timestamp_to_datetime(change_doc["timestamp"])
    year_change = dt_change.year
    month_change = dt_change.month
    week_change = dt_change.isocalendar()[1]
    day_change = dt_change.timetuple().tm_yday

    cursor_docs = month_cursor(db, month_change, year_change)

    monthly_scores = {}
    weekly_scores = {}
    daily_scores = {}

    sci_monthly_scores = {}
    sci_weekly_scores = {}
    sci_daily_scores = {}

    tech_monthly_scores = {}
    tech_weekly_scores = {}
    tech_daily_scores = {}

    for doc in cursor_docs:
        doc["readOrNot"] = 1
        aid = doc["aid"]

        doc_date = timestamp_to_datetime(doc["timestamp"])
        doc_week = doc_date.isocalendar()[1]
        doc_day = doc_date.timetuple().tm_yday

        if aid not in monthly_scores:
            monthly_scores[aid] = 0
            ts_mth = doc["timestamp"]
        monthly_scores[aid] += (
            int(doc["readOrNot"])
            + int(doc["commentOrNot"])
            + int(doc["agreeOrNot"])
            + int(doc["shareOrNot"])
        )

        if doc_week == week_change:
            if aid not in weekly_scores:
                weekly_scores[aid] = 0
                ts_wk = doc["timestamp"]
            weekly_scores[aid] += (
                int(doc["readOrNot"])
                + int(doc["commentOrNot"])
                + int(doc["agreeOrNot"])
                + int(doc["shareOrNot"])
            )

        if doc_day == day_change:
            if aid not in daily_scores:
                daily_scores[aid] = 0
                ts_day = doc["timestamp"]
            daily_scores[aid] += (
                int(doc["readOrNot"])
                + int(doc["commentOrNot"])
                + int(doc["agreeOrNot"])
                + int(doc["shareOrNot"])
            )

        if change_doc["category"] == "science" and doc["category"] == "science":
            if aid not in sci_monthly_scores:
                sci_monthly_scores[aid] = 0
            sci_monthly_scores[aid] += (
                int(doc["readOrNot"])
                + int(doc["commentOrNot"])
                + int(doc["agreeOrNot"])
                + int(doc["shareOrNot"])
            )

            if doc_week == week_change:
                if aid not in sci_weekly_scores:
                    sci_weekly_scores[aid] = 0
                sci_weekly_scores[aid] += (
                    int(doc["readOrNot"])
                    + int(doc["commentOrNot"])
                    + int(doc["agreeOrNot"])
                    + int(doc["shareOrNot"])
                )

            if doc_day == day_change:
                if aid not in sci_daily_scores:
                    sci_daily_scores[aid] = 0
                sci_daily_scores[aid] += (
                    int(doc["readOrNot"])
                    + int(doc["commentOrNot"])
                    + int(doc["agreeOrNot"])
                    + int(doc["shareOrNot"])
                )

        if change_doc["category"] == "technology" and doc["category"] == "technology":
            if aid not in tech_monthly_scores:
                tech_monthly_scores[aid] = 0
            tech_monthly_scores[aid] += (
                int(doc["readOrNot"])
                + int(doc["commentOrNot"])
                + int(doc["agreeOrNot"])
                + int(doc["shareOrNot"])
            )

            if doc_week == week_change:
                if aid not in tech_weekly_scores:
                    tech_weekly_scores[aid] = 0
                tech_weekly_scores[aid] += (
                    int(doc["readOrNot"])
                    + int(doc["commentOrNot"])
                    + int(doc["agreeOrNot"])
                    + int(doc["shareOrNot"])
                )

            if doc_day == day_change:
                if aid not in tech_daily_scores:
                    tech_daily_scores[aid] = 0
                tech_daily_scores[aid] += (
                    int(doc["readOrNot"])
                    + int(doc["commentOrNot"])
                    + int(doc["agreeOrNot"])
                    + int(doc["shareOrNot"])
                )

    top5_mth = top5_from_scores(monthly_scores)
    top5_wk = top5_from_scores(weekly_scores)
    top5_day = top5_from_scores(daily_scores)

    pop_mth = {
        "_id": "m" + str(ts_mth),
        "timestamp": ts_mth,
        "articleAidList": top5_mth,
        "temporalGranularity:": "monthly",
    }

    pop_wk = {
        "_id": "w" + str(ts_wk),
        "timestamp": ts_wk,
        "articleAidList": top5_wk,
        "temporalGranularity:": "weekly",
    }

    pop_day = {
        "_id": "d" + str(ts_day),
        "timestamp": ts_day,
        "articleAidList": top5_day,
        "temporalGranularity:": "daily",
    }

    db.pop_ranks.replace_one({"_id": pop_mth["_id"]}, pop_mth, upsert=True)
    db.pop_ranks.replace_one({"_id": pop_wk["_id"]}, pop_wk, upsert=True)
    db.pop_ranks.replace_one({"_id": pop_day["_id"]}, pop_day, upsert=True)

    print("db.popRank updated")
    print("db.popRankMth: ", pop_mth)
    print("db.popRankWk: ", pop_wk)
    print("db.popRankDay: ", pop_day)


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    with db.reads.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for event in stream:
            change = event["fullDocument"]
            change["readOrNot"] = 1
            print("change: ", change)

            update_bereads(db, change)
            update_pop_ranks(db, change)


if __name__ == "__main__":
    main()
