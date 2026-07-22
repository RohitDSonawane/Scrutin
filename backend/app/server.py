"""
Scrutin — Uvicorn server entrypoint.

Usage:
    python -m app.server
    PORT=9000 python -m app.server
"""

from __future__ import annotations

import os
import sys

import uvicorn


def main() -> None:
    port_str = os.getenv("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        print(f"[ERROR] Invalid PORT value: '{port_str}'. Must be an integer.", file=sys.stderr)
        sys.exit(1)

    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Scrutin API server on http://{host}:{port}")
    print(f"  Swagger UI  -> http://localhost:{port}/api/docs")
    print(f"  Health      -> http://localhost:{port}/api/healthz")
    print(f"  Verify      -> POST http://localhost:{port}/api/verify")

    uvicorn.run(
        "app.api:app",
        host=host,
        port=port,
        reload=os.getenv("SCRUTIN_DEV", "false").lower() == "true",
        log_level="info",
    )


if __name__ == "__main__":
    main()
