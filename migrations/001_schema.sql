CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    student TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT 'General',
    day DATE NOT NULL,
    seconds INT NOT NULL CHECK (seconds >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS sessions_student ON sessions (student, day DESC);
CREATE INDEX IF NOT EXISTS sessions_day ON sessions (day DESC);
