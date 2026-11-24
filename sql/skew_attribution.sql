CREATE TABLE IF NOT EXISTS skew_verdicts (row_id TEXT PRIMARY KEY, feature_name TEXT, blamed_side TEXT);
SELECT blamed_side, COUNT(*) FROM skew_verdicts GROUP BY blamed_side;
