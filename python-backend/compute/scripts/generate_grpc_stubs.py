#!/usr/bin/env python3
"""Generate Python gRPC stubs from go-backend/internal/proto/ipc/ipc.proto.

Run from repo root: python python-backend/scripts/generate_grpc_stubs.py
Requires: grpcio-tools (pip install grpcio-tools)
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTO_DIR = REPO_ROOT / "go-backend" / "internal" / "proto"
PROTO_FILE = PROTO_DIR / "ipc" / "ipc.proto"
OUT_DIR = Path(__file__).resolve().parents[1] / "proto"  # python-backend/proto


def main() -> None:
    if not PROTO_FILE.exists():
        print(f"Proto file not found: {PROTO_FILE}")
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        "ipc/ipc.proto",
    ]
    result = subprocess.run(cmd, cwd=PROTO_DIR)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"Generated stubs in {OUT_DIR}")


if __name__ == "__main__":
    main()
