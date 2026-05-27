"""Export WS Pydantic models as JSON Schema for TS codegen.

Usage:
    uv run python backend/scripts/export_ws_schema.py > frontend/scripts/ws_schema.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make src/ importable when invoked from repo root
_BACKEND_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from pydantic import TypeAdapter  # noqa: E402

from agent.transport.ws_messages import WSInbound, WSOutbound  # noqa: E402


def main() -> None:
    inbound_schema = TypeAdapter(WSInbound).json_schema(ref_template="#/$defs/{model}")
    outbound_schema = TypeAdapter(WSOutbound).json_schema(ref_template="#/$defs/{model}")

    # 合并 — 两个 union 走同一个 schema 文档,$defs 共享
    inbound_defs = inbound_schema.pop("$defs", {})
    outbound_defs = outbound_schema.pop("$defs", {})
    merged_defs = {**outbound_defs, **inbound_defs}

    combined = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "WSMessages",
        "type": "object",
        "properties": {
            "WSInbound": inbound_schema,
            "WSOutbound": outbound_schema,
        },
        "$defs": merged_defs,
    }
    json.dump(combined, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
