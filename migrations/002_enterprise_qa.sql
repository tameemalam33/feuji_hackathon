-- Enterprise QA: run quality columns + test case page/root_cause
ALTER TABLE runs ADD COLUMN accessibility_score REAL;
ALTER TABLE runs ADD COLUMN security_score REAL;
ALTER TABLE test_cases ADD COLUMN page TEXT;
ALTER TABLE test_cases ADD COLUMN root_cause TEXT;
