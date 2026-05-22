-- P4-4: speed up admin events lookups by run/thread and event type.
-- Current Cascade schema names these columns run_id, event_name, and created_at.
CREATE INDEX IF NOT EXISTS idx_events_thread_ts
  ON events(run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_ts
  ON events(event_name, created_at DESC);
