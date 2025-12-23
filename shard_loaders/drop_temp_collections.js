use readersDb;

const tmpCollections = [
  "aid_cat_ts",
  "bereads_unsharded",
  "daily_pop_ranks",
  "montly_pop_ranks",
  "pop_ranks_unsharded",
  "reads_unsharded",
  "uid_reg",
  "weekly_pop_ranks",
];

tmpCollections.forEach(name => db[name].drop());
