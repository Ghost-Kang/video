"""Back-compat re-exports for Cascade persistence.

New code should import from agent.cascade.persistence.* or agent.cascade.services.*.
"""

from agent.cascade.persistence.analyses_repo import (
    load_latest_analysis_for_source,
    load_analysis,
    load_analysis_for_source,
    save_analysis,
    set_analysis_context,
)
from agent.cascade.persistence.db import bootstrap_schema, db_path, session, utc_now_rfc3339
from agent.cascade.persistence.events_repo import list_events, save_event, sum_generation_cost
from agent.cascade.persistence.rewrites_repo import (
    load_recent_rewrite,
    load_rewrite_by_id,
    save_rewrite,
)
from agent.cascade.persistence.toprador_cache_repo import (
    _load_toprador_cache_entry,
    cleanup_expired_toprador_cache,
    load_toprador_cache,
    save_toprador_cache,
)
from agent.cascade.services.creators_service import list_creators
from agent.cascade.services.retention import retention_sweep

__all__ = [
    "bootstrap_schema",
    "cleanup_expired_toprador_cache",
    "db_path",
    "_load_toprador_cache_entry",
    "list_creators",
    "list_events",
    "load_analysis",
    "load_analysis_for_source",
    "load_latest_analysis_for_source",
    "load_recent_rewrite",
    "load_rewrite_by_id",
    "load_toprador_cache",
    "retention_sweep",
    "save_analysis",
    "save_event",
    "save_rewrite",
    "save_toprador_cache",
    "session",
    "set_analysis_context",
    "sum_generation_cost",
    "utc_now_rfc3339",
]
