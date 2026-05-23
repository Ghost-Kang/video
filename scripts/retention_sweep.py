"""Run the P4-7 events retention sweep once.

Usage:
    cd backend && uv run python ../scripts/retention_sweep.py
"""

from __future__ import annotations

import asyncio
import json

from agent.cascade.storage import retention_sweep


async def _main() -> None:
    deleted = await retention_sweep()
    print(json.dumps({"deleted": deleted}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
