#!/usr/bin/env python3
"""Prove mcp/server.py works, over both transports, with nothing queued.

    mcp/selftest.py              # stdio, then HTTP
    mcp/selftest.py --stdio      # only the stdio conversation
    mcp/selftest.py --http       # only the HTTP conversation
    mcp/selftest.py --port 8899  # a different port for the HTTP part

The stdio part is `mcp/server.py --selftest`: it starts a child server on a
pipe, speaks MCP to it, calls read-only tools, checks that a path outside the
allowed folders and a badly typed argument come back as messages rather than
tracebacks, and checks that closing stdin shuts the server down.

The HTTP part starts `mcp/server.py --http` on a loopback port, posts the same
handshake and a read-only tool call to it, checks that a GET is refused because
this server answers POST only, and then stops it.

It queues no generation job and runs no Blender job, so it is safe while
someone else is using the graphics card. Exit 0 when everything passed.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server.py"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(url: str, message: dict, timeout: float = 120.0) -> tuple[int, dict | None]:
    data = json.dumps(message).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


def http_selftest(port: int) -> int:
    url = f"http://127.0.0.1:{port}/"
    child = subprocess.Popen([sys.executable, str(SERVER), "--http", "--port", str(port)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    failures: list[str] = []
    checks = 0

    def check(label: str, ok: bool, detail: str = ""):
        nonlocal checks
        checks += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"  {detail}" if not ok else ""))
        if not ok:
            failures.append(label)

    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            print(f"  FAIL  the HTTP server never opened port {port}")
            return 1

        status, reply = post(url, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                   "params": {"protocolVersion": "2025-06-18",
                                              "capabilities": {},
                                              "clientInfo": {"name": "http-selftest",
                                                             "version": "1"}}})
        check("initialize over HTTP returns 200 and a protocol version",
              status == 200 and (reply or {}).get("result", {}).get("protocolVersion"),
              f"status {status} {reply}")

        status, reply = post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        check("a notification is accepted with 202 and no body",
              status == 202 and reply is None, f"status {status} {reply}")

        status, reply = post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = (reply or {}).get("result", {}).get("tools", [])
        check("tools/list over HTTP returns the tools", status == 200 and len(tools) > 10,
              f"status {status}, {len(tools)} tools")

        status, reply = post(url, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                   "params": {"name": "list_graphs", "arguments": {}}})
        text = "".join(c.get("text", "")
                       for c in (reply or {}).get("result", {}).get("content", []))
        check("a read-only tool runs over HTTP",
              status == 200 and "txt2img_sdxl" in text, text[:160])

        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                code = r.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        check("a GET is refused with 405, because this server answers POST only",
              code == 405, f"got {code}")
    finally:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()

    print(f"\n{checks - len(failures)}/{checks} HTTP checks passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdio", action="store_true", help="only the stdio conversation")
    ap.add_argument("--http", action="store_true", help="only the HTTP conversation")
    ap.add_argument("--port", type=int, default=0,
                    help="port for the HTTP part (default: a free one)")
    args = ap.parse_args()
    both = not (args.stdio or args.http)
    failed = 0
    if both or args.stdio:
        print("stdio:")
        failed |= subprocess.run([sys.executable, str(SERVER), "--selftest"]).returncode
    if both or args.http:
        print("\nHTTP:")
        failed |= http_selftest(args.port or free_port())
    print("\nselftest " + ("FAILED" if failed else "passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
