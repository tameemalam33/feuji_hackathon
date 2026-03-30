-- AutoQA Pro: advanced QA platform columns (also applied automatically in models/database.py init_db)
ALTER TABLE runs ADD COLUMN health_score REAL;
ALTER TABLE runs ADD COLUMN coverage REAL;
ALTER TABLE runs ADD COLUMN performance_score REAL;
ALTER TABLE runs ADD COLUMN insights_json TEXT;

ALTER TABLE test_cases ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE test_cases ADD COLUMN screenshot_path TEXT;
