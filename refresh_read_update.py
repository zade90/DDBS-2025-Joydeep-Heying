import pymongo
from pymongo import MongoClient
from datetime import datetime
import numpy as np

client = MongoClient('mongodb://localhost:27041')
db = client.readersDb

with db.reads.watch(
        [{'$match': {'operationType': 'insert'}}]) as stream:
        # can reasonably assume to only watch for inserts because read record cannot be undone or edited
    for change in stream:
        change = change['fullDocument']
        change['readOrNot']=1
        print("change: ", change)

        #################### update db.bereads/ db.sci_bereads ####################
        doc = db.bereads.find_one({"_id": change['aid']})
        doc['readOrNot']=1

        readNum = int(doc['readNum']) + 1
        readUidList = list(doc['readUidList'])
        if int(change['readOrNot']) > 0 and (change['uid'] not in readUidList):
            readUidList.append(change['uid'])

        commentNum = int(doc['commentNum']) + int(change['commentOrNot'])
        commentUidList = list(doc['commentUidList'])
        if int(change['commentOrNot']) > 0 and (change['uid'] not in commentUidList):
            commentUidList.append(change['uid'])

        agreeNum = int(doc['agreeNum']) + int(change['agreeOrNot'])
        agreeUidList = list(doc['agreeUidList'])
        if int(change['agreeOrNot']) > 0 and (change['agreeOrNot'] not in agreeUidList):
            agreeUidList.append(change['uid'])

        shareNum = int(doc['shareNum']) + int(change['shareOrNot'])
        shareUidList = list(doc['shareUidList'])
        if int(change['shareOrNot']) > 0 and (change['uid'] not in shareUidList):
            shareUidList.append(str(change['uid']))


        beread_dict = {
            "_id": doc['_id'],
            "category": doc['category'],
            "timestamp": doc['timestamp'],
            "readNum": readNum,
            "readUidList": readUidList,
            "commentNum": commentNum,
            "commentUidList": commentUidList,
            "agreeNum": agreeNum,
            "agreeUidList": agreeUidList,
            "shareNum": shareNum,
            "shareUidList": shareUidList,
            "aid": doc['aid'],
        }

        db.bereads.replace_one({"_id": change['aid']}, beread_dict)
        print("db.bereads updated: ", beread_dict)

        if change['category'] == "science":
            db.sci_bereads.replace_one({"_id": change['aid']}, beread_dict)
            print("db.sci_bereads also updated")

        date_change = datetime.fromtimestamp(int(change['timestamp'][:-3]))
        year_change = date_change.year
        month_change = date_change.month
        week_change = date_change.isocalendar()[1]
        day_change = date_change.timetuple().tm_yday

        cursor_docs = db.reads.find( { "$and": [{ "$expr": { "$eq": [{ "$month": {"$toDate": {"$toLong": "$timestamp"}}}, month_change]}},
                                               { "$expr": { "$eq": [{ "$year": {"$toDate": {"$toLong": "$timestamp"}}}, year_change]}} ]})


        art_popScore_mth = {}
        art_popScore_wk = {}
        art_popScore_day = {}

        art_popScoreSci_mth = {}
        art_popScoreSci_wk = {}
        art_popScoreSci_day = {}

        art_popScoreTech_mth = {}
        art_popScoreTech_wk = {}
        art_popScoreTech_day = {}
        for doc in cursor_docs:
            doc['readOrNot']=1
            aid = doc['aid']

            date_doc = datetime.fromtimestamp(int(doc['timestamp'][:-3]))
            wk = date_doc.isocalendar()[1]
            day = date_doc.timetuple().tm_yday

            ########################## update popRank ###############################
            if (aid not in art_popScore_mth):
                art_popScore_mth[aid] = 0
                ts_mth = doc['timestamp']
            art_popScore_mth[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

            if (wk == week_change):
                if (aid not in art_popScore_wk):
                    art_popScore_wk[aid] = 0
                    ts_wk = doc['timestamp']
                art_popScore_wk[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

            if (day == day_change):
                if (aid not in art_popScore_day):
                    art_popScore_day[aid] = 0
                    ts_day = doc['timestamp']
                art_popScore_day[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

            ##################### update science poprank ############################
            if (change['category'] == "science") and (doc['category'] == "science"):
                if (aid not in art_popScoreSci_mth):
                    art_popScoreSci_mth[aid] = 0
                art_popScoreSci_mth[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

                if (wk == week_change):
                    if (aid not in art_popScoreSci_wk):
                        art_popScoreSci_wk[aid] = 0
                    art_popScoreSci_wk[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

                if (day == day_change):
                    if (aid not in art_popScoreSci_day):
                        art_popScoreSci_day[aid] = 0
                    art_popScoreSci_day[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

            if (change['category'] == "technology") and (doc['category'] == "technology"):
                if (aid not in art_popScoreTech_mth):
                    art_popScoreTech_mth[aid] = 0
                art_popScoreTech_mth[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

                if (wk == week_change):
                    if (aid not in art_popScoreTech_wk):
                        art_popScoreTech_wk[aid] = 0
                    art_popScoreTech_wk[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

                if (day == day_change):
                    if (aid not in art_popScoreTech_day):
                        art_popScoreTech_day[aid] = 0
                    art_popScoreTech_day[aid] += int(doc['readOrNot']) + int(doc['commentOrNot']) + int(doc['agreeOrNot']) + int(doc['shareOrNot'])

        ############ update popRank ###################
        art_popScore_mth = np.array(sorted(art_popScore_mth.items(), key=lambda x: x[1], reverse=True))
        art_popScore_wk = np.array(sorted(art_popScore_wk.items(), key=lambda x: x[1], reverse=True))
        art_popScore_day = np.array(sorted(art_popScore_day.items(), key=lambda x: x[1], reverse=True))

        top5_mth = list(art_popScore_mth[:5, 0])
        top5_wk = list(art_popScore_wk[:5, 0])  
        top5_day = list(art_popScore_day[:5, 0])  

        popMth_dict = {
            "_id": "m" + str(ts_mth),
            "timestamp": ts_mth,
            "articleAidList": top5_mth,
            "temporalGranularity:": "monthly"
        }

        popWk_dict = {
            "_id": "w" + str(ts_wk),
            "timestamp": ts_wk,
            "articleAidList": top5_wk,
            "temporalGranularity:": "weekly"
        }

        popDay_dict = {
            "_id": "d" + str(ts_day),
            "timestamp": ts_day,
            "articleAidList": top5_day,
            "temporalGranularity:": "daily"
        }


        db.pop_ranks.replace_one({"_id": popMth_dict["_id"]}, popMth_dict, upsert=True)
        db.pop_ranks.replace_one({"_id": popWk_dict["_id"]}, popWk_dict, upsert=True)
        db.pop_ranks.replace_one({"_id": popDay_dict["_id"]}, popDay_dict, upsert=True)
        print("db.popRank updated")
        print("db.popRankMth: ", popMth_dict)
        print("db.popRankWk: ", popWk_dict)
        print("db.popRankDay: ", popDay_dict)

