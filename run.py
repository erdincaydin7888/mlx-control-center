#!/usr/bin/env python3
"""MLX Control Center — Launcher Script.

Usage:
    python run.py [--port PORT] [--host HOST]

Starts the FastAPI dashboard server.
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="MLX Control Center Dashboard")
    parser.add_argument("--port", type=int, default=8070, help="Dashboard port (default: 8070)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    # Ensure the backend package is importable
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_dir)

    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn not found. Install dependencies first:")
        print("   pip install -r requirements.txt")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════╗
│           MLX Control Center 🚀                  │
│                                                  │
│   Dashboard: http://{args.host}:{args.port}          │
│   Press Ctrl+C to stop                           │
╚══════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
