#!/usr/bin/env python3
"""Serve this repository's asset pipeline to an MCP client, over stdio or HTTP.

    mcp/server.py                     # speak MCP over stdin and stdout
    mcp/server.py --selftest          # start a copy, talk to it, check the replies
    mcp/server.py --list-tools        # names and one line each, no client needed
    mcp/server.py --http              # the same tools over HTTP on 127.0.0.1:8765
    mcp/server.py --http --port 9000  # another port, still on the loopback

Register it with Claude Code (the `--` is required, and the scope is `local`,
this project only, unless you pass `--scope user`):

    claude mcp add --transport stdio asset-engine -- python3 /asset-engine/mcp/server.py
    claude mcp list
    claude mcp get asset-engine
    claude mcp remove asset-engine

Or, when the server needs an environment of its own:

    claude mcp add-json asset-engine '{"type":"stdio","command":"python3",
      "args":["/asset-engine/mcp/server.py"],
      "env":{"ASSET_ENGINE_ROOT":"/asset-engine","MODELS_DIR":"/models"}}'

WHY THIS EXISTS. Every capability in this repository is a command-line script,
so driving the pipeline has needed a shell. An MCP client that has no shell,
or that is not on this machine, cannot run one. This wraps the scripts that are
safe to expose as MCP tools, so such a client can check the engine, look at what
is on disk, queue a graph, render a sheet and cut lip sync cues without ever
being handed a command line.

It is registered by hand, not shipped in the plugin: it needs the Docker socket
to reach Blender inside the ComfyUI container, and that is not something an
installer should acquire by installing a plugin.

THE PROTOCOL. Model Context Protocol, the handshake revisions: `2025-06-18` is
the preferred version, and `2025-11-25`, `2025-03-26` and `2024-11-05` are
accepted and echoed back. Messages are JSON-RPC 2.0. Over stdio each message is
one line of UTF-8 JSON on stdin, and the reply one line on stdout; nothing else
is ever written to stdout, and all logging goes to stderr. `initialize`,
`notifications/initialized`, `ping`, `tools/list`, `tools/call` and
`server/discover` are implemented. Every other method returns JSON-RPC error
-32601, and a malformed frame returns -32700 or -32600, never a traceback.
Shutdown is the transport closing: end of file on stdin, or SIGINT or SIGTERM,
and the process exits 0.

`server/discover` is the current revision's probe (`2026-07-28`). It is answered
so that a client which sends it first learns that this server speaks the older
handshake revisions and falls back to `initialize`. Per-request `_meta` version
negotiation is not implemented.

THE TOOLS. Each one wraps a script in this repository. Run `--list-tools` for
the current list with one line each. They are grouped by what they cost:

  read-only and fast   engine_health, list_graphs, validate_graphs, list_models,
                       list_animation_clips, list_prompt_folders, list_assets,
                       inspect_sprite_sheet, inspect_daz_library,
                       daz_library_list
  queue and generation run_graph, queue_status, interrupt_job, free_models
  Blender              render_sprite_sheet, bone_roles_map, bone_roles_compile,
                       face_rig_add_jaw, decimation_report, normalise_mesh
  lip sync             lipsync_cues, compose_mouths, preview_lipsync

WHAT IS DELIBERATELY ABSENT. Nothing here deletes, uninstalls or publishes.
There is no `cleanup.py sweep` and no `cleanup.py keep` (the sweep removes
files, and curating decides what a finished asset is, which is a person's
call); no `daz_library.py install` or `uninstall`; no `fetch_models.py
--download` (it writes tens of gigabytes and some weights carry a licence a
person must accept); no `publish_image.sh`; no container start, stop or
restart; and no arbitrary file read or write. A client that needs one of those
uses a shell, where a person can see what it is about to do.

SAFETY. Every path argument is resolved and then refused unless it lies under
`output/`, `input/` or the models directory, and anything written is refused
unless it lies under `output/`. A graph is named, not pathed: `run_graph` takes
`txt2img_sdxl`, resolved inside `workflows/api/`, so a path cannot escape
through it, and the same holds for role pose files and prompt folders. No
subprocess is ever run through a shell: every command is an argument list, so
nothing a caller sends is parsed as shell syntax. Every tool has a timeout, and
every result is capped in size. A tool reports the files it wrote by path and
size; it never returns their bytes.

THE ENVIRONMENT.

  ASSET_ENGINE_ROOT       the repository root (default /asset-engine)
  ASSET_ENGINE_CONTAINER  pin the ComfyUI container name; passed through to the
                          scripts, which otherwise ask Docker which one is up
  MODELS_DIR              where weights and the Daz library live; passed
                          through, and read from .env when it is not set, the
                          way scripts/fetch_models.py reads it
  COMFY_URL               the ComfyUI server (default http://127.0.0.1:8188)
  ASSET_ENGINE_PYTHON     the interpreter the scripts run under (default: the
                          first python3 on PATH; the repository's scripts want
                          the system python3, not .venv)
  ASSET_ENGINE_MCP_MAX_CHARS  cap on the text of one result (default 40000)

HTTP MODE has no authentication of its own and binds to 127.0.0.1 by default.
Anything other than the loopback needs https, which means a reverse proxy in
front of it and an authorisation check there: the MCP specification requires
https for a remote transport except on localhost, and this server speaks plain
HTTP. Bind it elsewhere only behind such a proxy. It accepts a JSON-RPC message
by POST and answers with a single JSON response; it does not implement
server-sent events, resumable streams or session identifiers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SERVER_NAME = "asset-engine"
SERVER_VERSION = "0.1.0"

# Handshake-based revisions this server speaks, newest first. The client's
# requested version is echoed back when it is one of these; otherwise the first
# is offered, and the client decides whether it can live with it.
PROTOCOL_VERSIONS = ("2025-06-18", "2025-11-25", "2025-03-26", "2024-11-05")
PREFERRED_PROTOCOL = "2025-06-18"

REPO = Path(os.environ.get("ASSET_ENGINE_ROOT", "/asset-engine")).resolve()
SCRIPTS = REPO / "scripts"
OUTPUT = REPO / "output"
INPUT = REPO / "input"
GRAPHS = REPO / "workflows" / "api"
ROLE_POSES = REPO / "poses" / "roles"
PROMPTS = REPO / "prompts"
ASSETS = OUTPUT / "assets"

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
MAX_CHARS = int(os.environ.get("ASSET_ENGINE_MCP_MAX_CHARS", "40000"))
MAX_LISTED_FILES = 40

# JSON-RPC 2.0 error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def log(message: str) -> None:
    """Everything the server has to say goes to stderr. Stdout is the protocol."""
    print(f"[{SERVER_NAME}] {message}", file=sys.stderr, flush=True)


def python_bin() -> str:
    override = os.environ.get("ASSET_ENGINE_PYTHON")
    if override:
        return override
    return shutil.which("python3") or sys.executable


def models_dir() -> Path | None:
    """MODELS_DIR from the environment, else from .env, resolved as compose does.

    The same rule as scripts/fetch_models.py: a relative value is resolved
    against the repository root, because that is where the compose file is.
    """
    raw = os.environ.get("MODELS_DIR")
    if not raw:
        env = REPO / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                line = line.strip()
                if line.startswith("MODELS_DIR="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not raw:
        return None
    return Path(raw) if os.path.isabs(raw) else (REPO / raw).resolve()


class ToolError(Exception):
    """A message a caller can act on. Never a traceback."""


# ------------------------------------------------------------------ path safety

def _real(path: Path) -> str:
    """The path with every symlink resolved, which is what containment is judged on.

    os.path.realpath resolves a path whose tail does not exist yet, so an
    output file that is about to be written is checked the same way as one that
    is already there.
    """
    return os.path.realpath(str(path))


def _contained(real: str, roots: list[Path]) -> bool:
    for root in roots:
        rroot = _real(root)
        if real == rroot or real.startswith(rroot.rstrip("/") + "/"):
            return True
    return False


def read_roots() -> list[Path]:
    roots = [OUTPUT, INPUT]
    mdir = models_dir()
    if mdir is not None:
        roots.append(mdir)
    return roots


def write_roots() -> list[Path]:
    return [OUTPUT]


def _roots_text(roots: list[Path]) -> str:
    return ", ".join(str(r) for r in roots)


def safe_path(raw, field: str, *, must_exist: bool = True, expect: str = "file",
              write: bool = False) -> Path:
    """Resolve a caller's path and refuse it unless it is inside an allowed root."""
    if not isinstance(raw, str) or not raw.strip():
        raise ToolError(f"{field}: expected a non-empty path")
    if "\x00" in raw:
        raise ToolError(f"{field}: a path may not contain a null byte")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO / path
    roots = write_roots() if write else read_roots()
    real = _real(path)
    if not _contained(real, roots):
        which = "written to" if write else "read"
        raise ToolError(
            f"{field}: {raw!r} resolves to {real}, which is outside the folders this "
            f"server may have {which}: {_roots_text(roots)}. "
            "Give a path under one of them.")
    resolved = Path(real)
    if must_exist and not resolved.exists():
        raise ToolError(f"{field}: no such path: {raw} (resolved to {real})")
    if resolved.exists():
        if expect == "file" and not resolved.is_file():
            raise ToolError(f"{field}: {raw} is not a file")
        if expect == "dir" and not resolved.is_dir():
            raise ToolError(f"{field}: {raw} is not a directory")
    return resolved


def out_path(raw, field: str, *, suffixes: tuple[str, ...] = ()) -> Path:
    """A path this server is allowed to write, with its parent folder made."""
    path = safe_path(raw, field, must_exist=False, expect="any", write=True)
    if suffixes and path.suffix.lower() not in suffixes:
        raise ToolError(f"{field}: expected one of {', '.join(suffixes)}, got {path.suffix or 'no suffix'}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def pick_name(raw, field: str, choices: list[str], hint: str) -> str:
    """One entry chosen from a list the server built, so no path can escape."""
    if not isinstance(raw, str) or not NAME_RE.match(raw):
        raise ToolError(f"{field}: expected a plain name, letters, digits, dot, dash "
                        f"or underscore. {hint}")
    if raw in choices:
        return raw
    stem = raw[:-5] if raw.endswith(".json") else raw
    for c in choices:
        if c == stem or c == stem + ".json":
            return c
    near = [c for c in choices if stem.lower() in c.lower()][:5]
    raise ToolError(f"{field}: no such entry {raw!r}. "
                    + (f"Did you mean {', '.join(near)}? " if near else "")
                    + hint)


def graph_names() -> list[str]:
    if not GRAPHS.is_dir():
        return []
    return sorted(p.name for p in GRAPHS.glob("*.json"))


def role_pose_names() -> list[str]:
    if not ROLE_POSES.is_dir():
        return []
    return sorted(p.name for p in ROLE_POSES.glob("*.json"))


def as_arg(path: Path) -> str:
    """How a path is handed to a script: repo-relative inside the repo, else absolute."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


# --------------------------------------------------------------- running things

def run(argv: list[str], timeout: float, label: str) -> tuple[int, str, str, float]:
    """Run a script. An argument list, never a shell string, so nothing is parsed
    as shell syntax. The child never sees this server's stdin or stdout."""
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    start = time.time()
    log(f"run {label}: {' '.join(argv)}")
    try:
        proc = subprocess.run(argv, cwd=str(REPO), env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout,
                              errors="replace")
    except FileNotFoundError as exc:
        raise ToolError(f"{label}: cannot run {argv[0]}: {exc}") from None
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"{label}: timed out after {timeout:.0f}s and was killed. "
            "Raise the tool's `timeout` argument, or run the job from a shell "
            "and watch it there.") from None
    except PermissionError as exc:
        raise ToolError(f"{label}: cannot run {argv[0]}: {exc}") from None
    return proc.returncode, proc.stdout, proc.stderr, time.time() - start


def clip(text: str, limit: int | None = None) -> str:
    limit = MAX_CHARS if limit is None else limit
    if len(text) <= limit:
        return text
    keep = limit // 2
    dropped = len(text) - 2 * keep
    return (text[:keep] + f"\n\n... [{dropped} characters cut from the middle; "
            f"the cap is {limit} characters] ...\n\n" + text[-keep:])


def files_since(since: float, roots: list[Path] | None = None) -> list[Path]:
    """Files under output/ whose mtime is at or after `since`, oldest first."""
    hits: list[Path] = []
    for root in (roots or [OUTPUT]):
        if not root.is_dir():
            continue
        for f in root.rglob("*"):
            try:
                if f.is_file() and f.stat().st_mtime >= since - 1:
                    hits.append(f)
            except OSError:
                continue
    hits.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0)
    return hits


def describe_files(paths: list[Path]) -> str:
    if not paths:
        return ""
    lines = ["", f"Files written ({len(paths)}):"]
    for f in paths[:MAX_LISTED_FILES]:
        try:
            kb = f.stat().st_size / 1024
        except OSError:
            kb = 0
        lines.append(f"  {as_arg(f)}  ({kb:.0f} KB)")
    if len(paths) > MAX_LISTED_FILES:
        lines.append(f"  ... and {len(paths) - MAX_LISTED_FILES} more")
    return "\n".join(lines)


def script_result(code: int, out: str, err: str, secs: float, *,
                  label: str, since: float | None = None,
                  error_codes: tuple[int, ...] = (), note: str = "") -> dict:
    """A tool result built from a script run: what it said, what it wrote, how it ended."""
    body = [f"{label}: exit code {code} after {secs:.1f}s"]
    if note:
        body.append(note)
    if out.strip():
        body.append("")
        body.append(out.rstrip())
    if err.strip():
        body.append("")
        body.append("stderr:")
        body.append(err.rstrip())
    if since is not None:
        written = describe_files(files_since(since))
        if written:
            body.append(written)
    is_error = code in error_codes if error_codes else code != 0
    return text_result("\n".join(body), is_error=is_error)


def text_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": clip(text) or "(no output)"}],
            "isError": bool(is_error)}


def comfy_get(path: str, timeout: float = 20.0):
    url = f"{COMFY_URL}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.URLError as exc:
        raise ToolError(
            f"cannot reach ComfyUI at {COMFY_URL}: {exc}. "
            "Run engine_health to see whether the container and the server are up."
        ) from None
    except (ValueError, TimeoutError, OSError) as exc:
        raise ToolError(f"cannot read {url}: {exc}") from None


# ------------------------------------------------------- argument validation

def validate(schema: dict, args: dict, tool: str) -> dict:
    """Check a caller's arguments against the tool's JSON Schema before anything runs.

    A small, explicit subset: type, enum, required, properties,
    additionalProperties, minimum, maximum, minLength, maxLength, pattern,
    items, minItems, maxItems and default. Every problem is reported at once,
    so a caller fixes one call rather than five.
    """
    if not isinstance(args, dict):
        raise ToolError(f"{tool}: arguments must be a JSON object, got {type(args).__name__}")
    props = schema.get("properties", {})
    problems: list[str] = []
    for key in args:
        if key not in props and schema.get("additionalProperties") is False:
            near = [p for p in props if key.lower() in p.lower() or p.lower() in key.lower()]
            problems.append(f"unknown argument {key!r}"
                            + (f" (did you mean {', '.join(near[:3])}?)" if near else "")
                            + f"; this tool takes {', '.join(sorted(props)) or 'none'}")
    for key in schema.get("required", []):
        if args.get(key) is None:
            problems.append(f"missing required argument {key!r}: "
                            f"{props.get(key, {}).get('description', '')}".rstrip(": "))
    clean: dict = {}
    for key, spec in props.items():
        if key not in args or args[key] is None:
            if "default" in spec:
                clean[key] = spec["default"]
            continue
        value = args[key]
        problems.extend(_check(value, spec, key))
        clean[key] = value
    if problems:
        raise ToolError(f"{tool}: " + "; ".join(problems))
    return clean


_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
          "array": list, "object": dict}


def _check(value, spec: dict, field: str) -> list[str]:
    problems: list[str] = []
    want = spec.get("type")
    if want:
        expect = _TYPES.get(want, object)
        ok = isinstance(value, expect) and not (want != "boolean" and isinstance(value, bool))
        if want == "integer" and isinstance(value, bool):
            ok = False
        if not ok:
            return [f"{field}: expected {want}, got {type(value).__name__}"]
    if "enum" in spec and value not in spec["enum"]:
        problems.append(f"{field}: expected one of {', '.join(map(str, spec['enum']))}, got {value!r}")
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            problems.append(f"{field}: shorter than {spec['minLength']} characters")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            problems.append(f"{field}: longer than {spec['maxLength']} characters")
        if "pattern" in spec and not re.match(spec["pattern"], value):
            problems.append(f"{field}: {value!r} does not match {spec['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            problems.append(f"{field}: below the minimum of {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            problems.append(f"{field}: above the maximum of {spec['maximum']}")
    if isinstance(value, list):
        if "minItems" in spec and len(value) < spec["minItems"]:
            problems.append(f"{field}: needs at least {spec['minItems']} items")
        if "maxItems" in spec and len(value) > spec["maxItems"]:
            problems.append(f"{field}: takes at most {spec['maxItems']} items")
        item = spec.get("items")
        if isinstance(item, dict):
            for i, entry in enumerate(value):
                problems.extend(_check(entry, item, f"{field}[{i}]"))
    return problems


def timeout_of(args: dict, default: float, cap: float) -> float:
    given = args.get("timeout")
    if given is None:
        return default
    return float(min(max(float(given), 1.0), cap))


# ------------------------------------------------------------------ the tools
# Each handler takes the validated arguments and returns a tool result. The
# schema beside it in TOOLS is what a client sees, so every description is
# written for a caller who cannot see this repository.

def t_engine_health(a: dict) -> dict:
    argv = [python_bin(), str(SCRIPTS / "doctor.py"), "--skip-models"]
    if a.get("format", "text") == "json":
        argv.append("--json")
    code, out, err, secs = run(argv, timeout_of(a, 180, 600), "doctor.py")
    meaning = {0: "everything the check covers is ready",
               1: "something is missing; the report says what and how to fix it",
               2: "the check could not run"}.get(code, "unexpected exit code")
    return script_result(code, out, err, secs, label="doctor.py --skip-models",
                         error_codes=(2,), note=f"exit {code}: {meaning}")


def t_list_graphs(a: dict) -> dict:
    contains = (a.get("contains") or "").lower()
    names = graph_names()
    if not names:
        raise ToolError(f"no graphs found under {GRAPHS}. Is ASSET_ENGINE_ROOT right? "
                        f"It is currently {REPO}.")
    lines = [f"{len(names)} API graphs under {as_arg(GRAPHS)}. "
             "run_graph takes the name, with or without .json.", ""]
    shown = 0
    for name in names:
        comment = ""
        try:
            graph = json.loads((GRAPHS / name).read_text())
            comment = " ".join(str(graph.get("_comment", "")).split())
        except (OSError, ValueError) as exc:
            comment = f"(could not read: {exc})"
        if contains and contains not in name.lower() and contains not in comment.lower():
            continue
        shown += 1
        lines.append(f"  {name[:-5]}")
        if comment:
            lines.append(f"      {comment[:600]}")
    if contains and not shown:
        lines.append(f"  (nothing matched {contains!r})")
    return text_result("\n".join(lines))


def t_validate_graphs(a: dict) -> dict:
    argv = [python_bin(), str(SCRIPTS / "validate_workflows.py")]
    if a.get("graph"):
        name = pick_name(a["graph"], "graph", graph_names(), "Run list_graphs for the names.")
        argv.append(as_arg(GRAPHS / name))
    code, out, err, secs = run(argv, timeout_of(a, 300, 900), "validate_workflows.py")
    return script_result(code, out, err, secs, label="validate_workflows.py")


def t_list_models(a: dict) -> dict:
    mode = a.get("mode", "groups")
    flag = {"groups": "--list-groups", "licences": "--licenses"}[mode]
    argv = [python_bin(), str(SCRIPTS / "fetch_models.py"), flag]
    code, out, err, secs = run(argv, timeout_of(a, 60, 300), "fetch_models.py")
    return script_result(code, out, err, secs, label=f"fetch_models.py {flag}")


def t_list_animation_clips(a: dict) -> dict:
    argv = [python_bin(), str(SCRIPTS / "list_animations.py")]
    if a.get("contains"):
        argv.append(a["contains"])
    code, out, err, secs = run(argv, timeout_of(a, 120, 600), "list_animations.py")
    return script_result(code, out, err, secs, label="list_animations.py")


def t_list_prompt_folders(a: dict) -> dict:
    if not PROMPTS.is_dir():
        raise ToolError(f"no prompts folder at {PROMPTS}")
    folders = sorted(p.name for p in PROMPTS.iterdir() if p.is_dir())
    if not a.get("folder"):
        lines = [f"Prompt folders under {as_arg(PROMPTS)}:", ""]
        for name in folders:
            files = sorted(f.name for f in (PROMPTS / name).glob("*.txt"))
            subjects = [f[:-4] for f in files if not f.startswith("_") and not f.endswith(".neg.txt")]
            lines.append(f"  {name}  ({len(subjects)} subjects)")
            if subjects:
                lines.append(f"      {', '.join(subjects[:24])}"
                             + (" ..." if len(subjects) > 24 else ""))
        loose = sorted(f.name for f in PROMPTS.glob("*.txt"))
        if loose:
            lines += ["", f"  loose files: {', '.join(loose)}"]
        lines += ["", "Give `folder` to list one folder's files, and `name` as well "
                      "to read one prompt's text."]
        return text_result("\n".join(lines))
    folder = pick_name(a["folder"], "folder", folders, f"The folders are: {', '.join(folders)}.")
    here = PROMPTS / folder
    files = sorted(f.name for f in here.iterdir() if f.is_file())
    if not a.get("name"):
        return text_result(f"{as_arg(here)}:\n\n" + "\n".join(f"  {f}" for f in files))
    chosen = pick_name(a["name"], "name", files + [f[:-4] for f in files if f.endswith(".txt")],
                       f"The files in {folder} are: {', '.join(files)}.")
    target = here / (chosen if chosen in files else chosen + ".txt")
    if not target.is_file():
        raise ToolError(f"name: no such prompt file: {folder}/{chosen}")
    body = target.read_text(errors="replace")
    return text_result(f"{as_arg(target)}  ({len(body)} characters)\n\n"
                       + clip(body, 6000))


def t_list_assets(a: dict) -> dict:
    if not ASSETS.is_dir():
        raise ToolError(f"no curated assets yet: {as_arg(ASSETS)} does not exist. "
                        "Assets land there when someone curates them from a shell.")
    names = sorted(p.name for p in ASSETS.iterdir() if p.is_dir())
    if not a.get("name"):
        lines = [f"{len(names)} curated assets under {as_arg(ASSETS)}:", ""]
        for name in names:
            parts = sorted(f.name for f in (ASSETS / name).iterdir())
            lines.append(f"  {name}  ({', '.join(parts[:8])}"
                         + (" ..." if len(parts) > 8 else "") + ")")
        lines += ["", "Give `name` for one asset's files and its recorded sources."]
        return text_result("\n".join(lines))
    name = pick_name(a["name"], "name", names, f"There are {len(names)} assets; "
                                               "call this tool with no arguments for the list.")
    here = ASSETS / name
    lines = [f"{as_arg(here)}:", ""]
    for f in sorted(here.rglob("*")):
        if f.is_file():
            lines.append(f"  {f.relative_to(here)}  ({f.stat().st_size / 1024:.0f} KB)")
    sources = here / "sources.json"
    if sources.is_file():
        lines += ["", "sources.json:", clip(sources.read_text(errors="replace"), 6000)]
    return text_result("\n".join(lines))


def t_inspect_sprite_sheet(a: dict) -> dict:
    sheet = safe_path(a["sheet"], "sheet")
    argv = [python_bin(), str(SCRIPTS / "sheet_check.py"), as_arg(sheet),
            "--cell", str(int(a["cell"]))]
    if a.get("azimuths"):
        argv += ["--azimuths", a["azimuths"]]
    if a.get("quiet"):
        argv.append("--quiet")
    code, out, err, secs = run(argv, timeout_of(a, 300, 900), "sheet_check.py")
    note = {0: "every check passed", 1: "a fault was found, or the sheet is smaller than one cell",
            2: "the sheet was not found, or the arguments were wrong"}.get(code, "")
    return script_result(code, out, err, secs, label="sheet_check.py",
                         error_codes=(2,), note=f"exit {code}: {note}")


def t_inspect_daz_library(a: dict) -> dict:
    mdir = models_dir()
    raw = a.get("directory")
    if not raw:
        if mdir is None:
            raise ToolError("directory: MODELS_DIR is not set and .env does not define it, "
                            "so there is no default library path. Give `directory`.")
        raw = str(mdir / "daz_library")
    library = safe_path(raw, "directory", expect="dir")
    argv = [python_bin(), str(SCRIPTS / "daz_inventory.py"), str(library)]
    if a.get("brief"):
        argv.append("--brief")
    if a.get("format", "text") == "json":
        argv.append("--json")
    code, out, err, secs = run(argv, timeout_of(a, 900, 3600), "daz_inventory.py")
    return script_result(code, out, err, secs, label="daz_inventory.py")


def t_daz_library_list(a: dict) -> dict:
    argv = [python_bin(), str(SCRIPTS / "daz_library.py"), "list"]
    if a.get("library"):
        argv += ["--library", str(safe_path(a["library"], "library", expect="dir"))]
    if a.get("format", "text") == "json":
        argv.append("--json")
    code, out, err, secs = run(argv, timeout_of(a, 120, 600), "daz_library.py list")
    return script_result(code, out, err, secs, label="daz_library.py list")


SET_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,80}=")


def t_run_graph(a: dict) -> dict:
    name = pick_name(a["graph"], "graph", graph_names(), "Run list_graphs for the names.")
    argv = [python_bin(), str(SCRIPTS / "run_workflow.py"), as_arg(GRAPHS / name)]
    if a.get("subject") is not None and a.get("prompt") is not None:
        raise ToolError("give `subject` or `prompt`, not both: `subject` fills the preset's "
                        "SUBJECT slot and keeps the house technique around it, while `prompt` "
                        "replaces the whole positive text.")
    for flag in ("subject", "prompt", "negative"):
        if a.get(flag) is not None:
            argv += [f"--{flag}", a[flag]]
    if a.get("image"):
        argv += ["--image", as_arg(safe_path(a["image"], "image"))]
    for spec in a.get("set", []):
        if not SET_RE.match(spec):
            raise ToolError(f"set: {spec!r} is not `name=value` or `NodeTitle.widget=value`")
        argv += ["--set", spec]
    if a.get("dry_run"):
        argv.append("--dry-run")
    since = time.time()
    code, out, err, secs = run(argv, timeout_of(a, 900, 7200), "run_workflow.py")
    return script_result(code, out, err, secs, label=f"run_workflow.py {name}", since=since)


def t_queue_status(a: dict) -> dict:
    queue = comfy_get("/queue")
    running = queue.get("queue_running", [])
    pending = queue.get("queue_pending", [])
    lines = [f"ComfyUI at {COMFY_URL}",
             f"  running: {len(running)}",
             f"  pending: {len(pending)}"]

    def ids(entries):
        out = []
        for entry in entries:
            if isinstance(entry, list) and len(entry) > 1:
                out.append(str(entry[1]))
        return out

    if running:
        lines.append("  running prompt ids: " + ", ".join(ids(running)))
    if pending:
        lines.append("  pending prompt ids: " + ", ".join(ids(pending)[:20]))
    if not running and not pending:
        lines.append("  the queue is empty, so a job started now runs at once")
    if a.get("raw"):
        lines += ["", clip(json.dumps(queue, indent=2), 8000)]
    return text_result("\n".join(lines))


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def t_interrupt_job(a: dict) -> dict:
    job = a["prompt_id"]
    if not ID_RE.match(job):
        raise ToolError("prompt_id: expected the id ComfyUI returned when the job was "
                        "queued, letters, digits, dot, dash or underscore")
    argv = [python_bin(), str(SCRIPTS / "run_workflow.py"), "--interrupt", job]
    code, out, err, secs = run(argv, timeout_of(a, 60, 300), "run_workflow.py --interrupt")
    return script_result(code, out, err, secs, label="run_workflow.py --interrupt")


def t_free_models(a: dict) -> dict:
    argv = [python_bin(), str(SCRIPTS / "run_workflow.py"), "--free"]
    code, out, err, secs = run(argv, timeout_of(a, 180, 600), "run_workflow.py --free")
    return script_result(code, out, err, secs, label="run_workflow.py --free")


POSES_RE = re.compile(r"^(static|even:\d{1,3}|frames:\d{1,6}(,\d{1,6})*|transforms:.+)$")


def t_render_sprite_sheet(a: dict) -> dict:
    model = safe_path(a["model"], "model")
    poses = a.get("poses", "static")
    if not POSES_RE.match(poses):
        raise ToolError("poses: expected `static`, `even:N`, `frames:1,7,13` or "
                        "`transforms:output/poses/FILE.json`")
    if poses.startswith("transforms:"):
        transforms = safe_path(poses.split(":", 1)[1], "poses (the transforms file)")
        poses = "transforms:" + as_arg(transforms)
    argv = [python_bin(), str(SCRIPTS / "render_sheet.py"), as_arg(model), "--poses", poses]
    for flag, key in (("--angles", "angles"), ("--size", "size"), ("--zoom", "zoom"),
                      ("--elevation", "elevation"), ("--azimuth-start", "azimuth_start"),
                      ("--engine", "engine"), ("--samples", "samples")):
        if a.get(key) is not None:
            argv += [flag, str(a[key])]
    if a.get("clay"):
        argv.append("--clay")
    if a.get("flat"):
        argv.append("--flat")
    if a.get("check"):
        argv.append("--check")
    if a.get("out"):
        argv += ["--out", as_arg(out_path(a["out"], "out", suffixes=(".png",)))]
    inner = int(timeout_of(a, 1800, 7200))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "render_sheet.py")
    return script_result(code, out, err, secs, label="render_sheet.py", since=since)


def t_bone_roles_map(a: dict) -> dict:
    rig = safe_path(a["rig"], "rig")
    argv = [python_bin(), str(SCRIPTS / "bone_roles.py"), "map", as_arg(rig)]
    if a.get("out"):
        argv += ["--out", as_arg(out_path(a["out"], "out", suffixes=(".json",)))]
    inner = int(timeout_of(a, 900, 3600))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "bone_roles.py map")
    return script_result(code, out, err, secs, label="bone_roles.py map", since=since)


def t_bone_roles_compile(a: dict) -> dict:
    pose = pick_name(a["role_poses"], "role_poses", role_pose_names(),
                     f"The role poses are: {', '.join(n[:-5] for n in role_pose_names())}.")
    rig = safe_path(a["rig"], "rig")
    dest = out_path(a["out"], "out", suffixes=(".json",))
    argv = [python_bin(), str(SCRIPTS / "bone_roles.py"), "compile",
            as_arg(ROLE_POSES / pose), as_arg(rig), "--out", as_arg(dest)]
    if a.get("feet"):
        argv += ["--feet", a["feet"]]
    inner = int(timeout_of(a, 900, 3600))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "bone_roles.py compile")
    return script_result(code, out, err, secs, label="bone_roles.py compile", since=since)


def t_face_rig_add_jaw(a: dict) -> dict:
    model = safe_path(a["model"], "model")
    dest = out_path(a["out"], "out", suffixes=(".blend", ".fbx"))
    argv = [python_bin(), str(SCRIPTS / "face_rig.py"), "add-jaw", as_arg(model),
            "--out", as_arg(dest)]
    if a.get("head"):
        argv += ["--head", a["head"]]
    if a.get("name"):
        argv += ["--name", a["name"]]
    if a.get("front"):
        argv += ["--front", a["front"]]
    inner = int(timeout_of(a, 900, 3600))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "face_rig.py add-jaw")
    return script_result(code, out, err, secs, label="face_rig.py add-jaw", since=since)


def t_decimation_report(a: dict) -> dict:
    model = safe_path(a["model"], "model")
    argv = [python_bin(), str(SCRIPTS / "decimation_report.py"), as_arg(model)]
    if a.get("faces"):
        if not re.match(r"^\d{2,8}(,\d{2,8})*$", a["faces"]):
            raise ToolError("faces: expected a comma separated list of face counts, "
                            "such as 50000,18000,8000")
        argv += ["--faces", a["faces"]]
    if a.get("sprite") is not None:
        argv += ["--sprite", str(int(a["sprite"]))]
    if a.get("target_iou") is not None:
        argv += ["--target-iou", str(float(a["target_iou"]))]
    if a.get("json_out"):
        argv += ["--json", as_arg(out_path(a["json_out"], "json_out", suffixes=(".json",)))]
    inner = int(timeout_of(a, 3600, 7200))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "decimation_report.py")
    return script_result(code, out, err, secs, label="decimation_report.py", since=since)


def t_normalise_mesh(a: dict) -> dict:
    if (a.get("height") is None) == (a.get("footprint") is None):
        raise ToolError("give exactly one of `height` (scale the Z extent, for anything "
                        "that stands) or `footprint` (scale the larger of X and Y, for "
                        "anything tile bound)")
    models = [safe_path(m, f"models[{i}]") for i, m in enumerate(a["models"])]
    argv = [python_bin(), str(SCRIPTS / "normalise_mesh.py")] + [as_arg(m) for m in models]
    if a.get("height") is not None:
        argv += ["--height", str(float(a["height"]))]
    else:
        argv += ["--footprint", str(float(a["footprint"]))]
    check = bool(a.get("check"))
    if check:
        argv.append("--check")
    else:
        suffix = a.get("suffix", "_norm")
        out_dir = a.get("out_dir")
        if not suffix and not out_dir:
            raise ToolError("suffix: an empty suffix overwrites the source mesh in place, "
                            "which this server will not do. Give a `suffix` such as _norm, "
                            "or an `out_dir` under output/.")
        if suffix:
            argv += ["--suffix", suffix]
        if out_dir:
            argv += ["--out-dir", as_arg(out_path(out_dir, "out_dir"))]
    inner = int(timeout_of(a, 1800, 7200))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "normalise_mesh.py")
    return script_result(code, out, err, secs, label="normalise_mesh.py",
                         since=None if check else since)


def t_lipsync_cues(a: dict) -> dict:
    source = safe_path(a["audio"], "audio", expect="any")
    argv = [python_bin(), str(SCRIPTS / "lipsync_cues.py"), as_arg(source)]
    if a.get("text") is not None:
        argv += ["--text", a["text"]]
    elif a.get("no_text"):
        argv.append("--no-text")
    if a.get("out"):
        argv += ["--out", as_arg(out_path(a["out"], "out"))]
    if a.get("fps") is not None:
        argv += ["--fps", str(float(a["fps"]))]
    if a.get("rule"):
        argv += ["--rule", a["rule"]]
    if a.get("recognizer"):
        argv += ["--recognizer", a["recognizer"]]
    inner = int(timeout_of(a, 900, 3600))
    argv += ["--timeout", str(inner)]
    since = time.time()
    code, out, err, secs = run(argv, inner + 120, "lipsync_cues.py")
    return script_result(code, out, err, secs, label="lipsync_cues.py", since=since)


def t_compose_mouths(a: dict) -> dict:
    since = time.time()
    if a.get("check"):
        manifest = safe_path(a["check"], "check")
        argv = [python_bin(), str(SCRIPTS / "compose_mouths.py"), "--check", as_arg(manifest)]
        code, out, err, secs = run(argv, timeout_of(a, 600, 1800), "compose_mouths.py --check")
        return script_result(code, out, err, secs, label="compose_mouths.py --check")
    for key in ("portrait", "box", "edits"):
        if not a.get(key):
            raise ToolError(f"{key}: required unless you pass `check` to re-check a manifest")
    portrait = safe_path(a["portrait"], "portrait")
    edits = safe_path(a["edits"], "edits", expect="dir")
    if not re.match(r"^\d{1,5},\d{1,5},\d{1,5},\d{1,5}$", a["box"]):
        raise ToolError("box: expected X,Y,W,H in the portrait's own pixels, such as 410,440,204,190")
    argv = [python_bin(), str(SCRIPTS / "compose_mouths.py"), as_arg(portrait),
            "--box", a["box"], "--edits", as_arg(edits)]
    if a.get("out"):
        argv += ["--out", as_arg(out_path(a["out"], "out"))]
    if a.get("feather") is not None:
        argv += ["--feather", str(int(a["feather"]))]
    if a.get("ring") is not None:
        argv += ["--ring", str(int(a["ring"]))]
    code, out, err, secs = run(argv, timeout_of(a, 600, 1800), "compose_mouths.py")
    return script_result(code, out, err, secs, label="compose_mouths.py", since=since)


def t_preview_lipsync(a: dict) -> dict:
    manifest = safe_path(a["manifest"], "manifest")
    argv = [python_bin(), str(SCRIPTS / "preview_lipsync.py"), as_arg(manifest)]
    if a.get("timeline"):
        argv.append(as_arg(safe_path(a["timeline"], "timeline")))
    if a.get("audio"):
        argv += ["--audio", as_arg(safe_path(a["audio"], "audio"))]
    if a.get("out"):
        argv += ["--out", as_arg(out_path(a["out"], "out", suffixes=(".mp4",)))]
    if a.get("sheet"):
        argv += ["--sheet", as_arg(out_path(a["sheet"], "sheet", suffixes=(".png",)))]
    if a.get("no_sheet"):
        argv.append("--no-sheet")
    if a.get("label"):
        argv.append("--label")
    if a.get("height") is not None:
        argv += ["--height", str(int(a["height"]))]
    since = time.time()
    code, out, err, secs = run(argv, timeout_of(a, 900, 3600), "preview_lipsync.py")
    return script_result(code, out, err, secs, label="preview_lipsync.py", since=since)


# ------------------------------------------------------------- the tool table

def _obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": required or [], "additionalProperties": False}


_TIMEOUT = {"type": "integer", "minimum": 1,
            "description": "seconds to wait before the run is killed; the tool's own "
                           "default is used when this is left out"}
_PATH = "a path under output/ or input/, or an absolute path inside one of them"

TOOLS: list[dict] = [
    {
        "name": "engine_health",
        "title": "Engine health check",
        "group": "read-only",
        "description":
            "Check that the asset engine can actually run, and say what to do about "
            "anything that cannot: Docker, the GPU runtime, the container, the ComfyUI "
            "server, the node packs, Blender, and the output folders. Model weights are "
            "skipped because checking them is slow. Run this first when anything else "
            "fails: almost every confusing failure in this pipeline is one of these. "
            "Takes a few seconds. Exit 1 means something is missing, which is a finding, "
            "not a server fault.",
        "inputSchema": _obj({
            "format": {"type": "string", "enum": ["text", "json"], "default": "text",
                       "description": "text is the readable report; json is the same "
                                      "report as one machine-readable object"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_engine_health,
    },
    {
        "name": "list_graphs",
        "title": "List generation graphs",
        "group": "read-only",
        "description":
            "List the ComfyUI API graphs this project ships, each with the note its "
            "author left on it, which usually says what it is for and what its licence "
            "allows. These names are what run_graph and validate_graphs take. Reads "
            "files on disk only, so it works with nothing running.",
        "inputSchema": _obj({
            "contains": {"type": "string", "maxLength": 80,
                         "description": "only graphs whose name or note contains this text"},
        }),
        "handler": t_list_graphs,
    },
    {
        "name": "validate_graphs",
        "title": "Validate graphs against the running server",
        "group": "read-only",
        "description":
            "Check every graph, or one named graph, against what the running ComfyUI "
            "actually loaded: a node class the server does not have, a widget name that "
            "does not exist on a node, or a required input left unwired. Catches in "
            "seconds what a queued job would report after minutes. Needs the ComfyUI "
            "server to be up, because it reads the server's node catalogue.",
        "inputSchema": _obj({
            "graph": {"type": "string", "maxLength": 80,
                      "description": "one graph name from list_graphs; all of them when "
                                     "this is left out"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_validate_graphs,
    },
    {
        "name": "list_models",
        "title": "List model groups and licences",
        "group": "read-only",
        "description":
            "List the model weight groups this project knows about and what each group "
            "is for, or the licence on every model and whether it permits commercial "
            "use. Reads the project's manifest only: it downloads nothing, contacts no "
            "host and creates no folders.",
        "inputSchema": _obj({
            "mode": {"type": "string", "enum": ["groups", "licences"], "default": "groups",
                     "description": "groups lists the groups and what they are for; "
                                    "licences lists every model's licence and whether it "
                                    "permits commercial use"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_list_models,
    },
    {
        "name": "list_animation_clips",
        "title": "List animation clips",
        "group": "read-only",
        "description":
            "List the animation clips the installed node packs can apply to a rigged "
            "mesh, by rig family, read out of the clip libraries on disk. Use it to find "
            "out what a character can be made to do before rigging one.",
        "inputSchema": _obj({
            "contains": {"type": "string", "maxLength": 80,
                         "description": "only clips or rigs whose name contains this text"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_list_animation_clips,
    },
    {
        "name": "list_prompt_folders",
        "title": "List prompt folders",
        "group": "read-only",
        "description":
            "List the folders of reusable subject prompts this project ships, such as "
            "buildings, characters and creatures, and the subjects in each. Give a "
            "folder to list its files, and a name as well to read one prompt's text. "
            "Reads only inside the project's prompt folder, and the text is capped.",
        "inputSchema": _obj({
            "folder": {"type": "string", "maxLength": 80,
                       "description": "one folder from the list, such as creatures"},
            "name": {"type": "string", "maxLength": 80,
                     "description": "one prompt in that folder, to read its text"},
        }),
        "handler": t_list_prompt_folders,
    },
    {
        "name": "list_assets",
        "title": "List curated assets",
        "group": "read-only",
        "description":
            "List the finished assets somebody has curated: for each one its concept "
            "image, model, rig, textures and pose sheets, and with a name given, its "
            "files with sizes and the recorded provenance of each generator and licence "
            "that produced it. Names the files; never returns their bytes.",
        "inputSchema": _obj({
            "name": {"type": "string", "maxLength": 80,
                     "description": "one asset name, for its files and recorded sources"},
        }),
        "handler": t_list_assets,
    },
    {
        "name": "inspect_sprite_sheet",
        "title": "Inspect a sprite sheet",
        "group": "read-only",
        "description":
            "Check a rendered sprite sheet for the faults that are arithmetic rather "
            "than taste: an empty cell, a subject cut by its cell border, and a row whose "
            "pose did nothing because it repeats the rest pose. Give the cell size in "
            "pixels, and the azimuth list of the render if you have it, and the facing of "
            "each column is named too. It cannot tell you whether the motion reads as the "
            "motion; that stays with a person. Needs the cell size, which is the pixels "
            "per cell the sheet was rendered at.",
        "inputSchema": _obj({
            "sheet": {"type": "string", "description": f"the sheet PNG: {_PATH}"},
            "cell": {"type": "integer", "minimum": 8, "maximum": 4096,
                     "description": "pixels per cell, the size the sheet was rendered at"},
            "azimuths": {"type": "string", "pattern": r"^-?\d+(\.\d+)?(,-?\d+(\.\d+)?)*$",
                         "description": "the render's azimuths, comma separated, such as "
                                        "45,135,225,315, so each column's facing is named"},
            "quiet": {"type": "boolean", "default": False,
                      "description": "print only the problems"},
            "timeout": _TIMEOUT,
        }, ["sheet", "cell"]),
        "handler": t_inspect_sprite_sheet,
    },
    {
        "name": "inspect_daz_library",
        "title": "Inspect a Daz content library",
        "group": "read-only",
        "description":
            "List what a Daz content library holds: figures with their vertex and polygon "
            "counts, bones, morphs and HD morphs, read straight out of the library's own "
            "files with no Daz Studio, Blender or GPU. Defaults to the library under the "
            "models directory. Reads only; the library is never modified, and its content "
            "never enters this repository. A large library takes minutes to walk.",
        "inputSchema": _obj({
            "directory": {"type": "string",
                          "description": "the library folder, or any folder inside one; "
                                         "must be under the models directory. Defaults to "
                                         "daz_library there"},
            "brief": {"type": "boolean", "default": False,
                      "description": "counts and headlines only, no per-file detail"},
            "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_inspect_daz_library,
    },
    {
        "name": "daz_library_list",
        "title": "List installed Daz products",
        "group": "read-only",
        "description":
            "List the Daz products recorded as installed in the content library, with the "
            "licence held for each. Reading only: this server cannot install or remove a "
            "product, because that is a purchase and a licence decision a person makes.",
        "inputSchema": _obj({
            "library": {"type": "string",
                        "description": "another library folder, under the models directory"},
            "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_daz_library_list,
    },
    {
        "name": "run_graph",
        "title": "Run a generation graph",
        "group": "queue",
        "description":
            "Queue one of this project's generation graphs on the ComfyUI server and wait "
            "for it, then name the files it wrote. Use `subject` on a preset graph: it "
            "fills the preset's subject slot and keeps the house technique around it. Use "
            "`prompt` on a plain graph, where it replaces the whole positive text. `set` "
            "overrides any other input, as name=value or NodeTitle.widget=value. TAKES "
            "MINUTES: an image is roughly a minute and a mesh several, on a shared "
            "server, so check queue_status first and raise `timeout` for a long job. Use "
            "`dry_run` to see the graph that would be sent without queueing anything.",
        "inputSchema": _obj({
            "graph": {"type": "string", "maxLength": 80,
                      "description": "a graph name from list_graphs, such as txt2img_sdxl"},
            "subject": {"type": "string", "maxLength": 4000,
                        "description": "fills a preset graph's subject slot, keeping the "
                                       "technique written around it"},
            "prompt": {"type": "string", "maxLength": 4000,
                       "description": "replaces the whole positive text; not with `subject`"},
            "negative": {"type": "string", "maxLength": 4000,
                         "description": "replaces the negative text"},
            "image": {"type": "string",
                      "description": f"an input image for an image-to-something graph: {_PATH}"},
            "set": {"type": "array", "maxItems": 40,
                    "items": {"type": "string", "maxLength": 400},
                    "description": "input overrides, each name=value or "
                                   "NodeTitle.widget=value, such as steps=20"},
            "dry_run": {"type": "boolean", "default": False,
                        "description": "build and print the graph, queue nothing"},
            "timeout": _TIMEOUT,
        }, ["graph"]),
        "handler": t_run_graph,
    },
    {
        "name": "queue_status",
        "title": "Queue status",
        "group": "queue",
        "description":
            "What the ComfyUI server is running and what is waiting, with the prompt id of "
            "each. Check this before queueing anything: the server is shared, and a job "
            "queued behind someone else's waits for it. Returns in a moment.",
        "inputSchema": _obj({
            "raw": {"type": "boolean", "default": False,
                    "description": "also include the server's raw queue JSON, capped"},
        }),
        "handler": t_queue_status,
    },
    {
        "name": "interrupt_job",
        "title": "Interrupt a queued or running job",
        "group": "queue",
        "description":
            "Stop the job with this prompt id. Interrupt your own job: the server is "
            "shared, so check queue_status first and be sure the id is yours. Files "
            "already written are left alone; nothing is deleted.",
        "inputSchema": _obj({
            "prompt_id": {"type": "string", "maxLength": 128,
                          "description": "the prompt id, as queue_status or run_graph reports it"},
            "timeout": _TIMEOUT,
        }, ["prompt_id"]),
        "handler": t_interrupt_job,
    },
    {
        "name": "free_models",
        "title": "Free the loaded models",
        "group": "queue",
        "description":
            "Ask the ComfyUI server to unload every model it is holding and release the "
            "memory. Use it when a job fails for want of VRAM. It costs the next job the "
            "reload time, and it affects everyone on the server, so do not do it while "
            "someone else's job is running: check queue_status first.",
        "inputSchema": _obj({"timeout": _TIMEOUT}),
        "handler": t_free_models,
    },
    {
        "name": "render_sprite_sheet",
        "title": "Render a sprite sheet",
        "group": "blender",
        "description":
            "Render a model to a sprite sheet, N angles across and one row per pose, using "
            "Blender inside the engine container. A static mesh gives one row; a rigged "
            "file can be sampled across its animation with poses `even:4`, at named frames "
            "with `frames:1,7,13`, or posed from a compiled transforms file with "
            "`transforms:output/poses/FILE.json`. TAKES MINUTES, and longer for many "
            "angles, a large size or many poses. Set `check` to run the arithmetic checks "
            "on the result in the same pass. The sheet is named, not returned.",
        "inputSchema": _obj({
            "model": {"type": "string",
                      "description": f"the .glb, .fbx or .blend to render: {_PATH}"},
            "poses": {"type": "string", "maxLength": 300, "default": "static",
                      "description": "static, even:N, frames:1,7,13, or "
                                     "transforms:PATH for a compiled pose file under output/"},
            "angles": {"type": "integer", "minimum": 1, "maximum": 32,
                       "description": "columns, one per facing (default 4)"},
            "size": {"type": "integer", "minimum": 32, "maximum": 2048,
                     "description": "pixels per cell (default 256)"},
            "zoom": {"type": "number", "minimum": 0.1, "maximum": 10,
                     "description": "framing, higher fills the cell more (default 1.15)"},
            "elevation": {"type": "number", "minimum": -90, "maximum": 90,
                          "description": "camera elevation in degrees (default 30)"},
            "azimuth_start": {"type": "number", "minimum": -360, "maximum": 360,
                              "description": "azimuth of the first column (default 45)"},
            "engine": {"type": "string", "enum": ["cycles", "eevee"],
                       "description": "renderer; cycles is the default and runs on the card"},
            "samples": {"type": "integer", "minimum": 1, "maximum": 4096,
                        "description": "render samples, fewer is faster and noisier"},
            "clay": {"type": "boolean", "default": False,
                     "description": "untextured clay render, for reading the form"},
            "flat": {"type": "boolean", "default": False,
                     "description": "flat unlit render, for silhouettes"},
            "check": {"type": "boolean", "default": False,
                      "description": "also run the sheet checks on the result"},
            "out": {"type": "string",
                    "description": "where to write the sheet PNG; must be under output/"},
            "timeout": _TIMEOUT,
        }, ["model"]),
        "handler": t_render_sprite_sheet,
    },
    {
        "name": "bone_roles_map",
        "title": "Map a rig's bones to roles",
        "group": "blender",
        "description":
            "Work out what each bone of a generated rig is, from the skeleton's geometry "
            "and its skin weights, and print the table: root, pelvis, legs, spine, head "
            "and the rest. Automatic rigs name every bone bone_0 to bone_N, so this is how "
            "a pose written for no particular rig is aimed at this one. Writes a roles "
            "file beside the rig, or where `out` says. Runs Blender in the container and "
            "takes a minute or two.",
        "inputSchema": _obj({
            "rig": {"type": "string", "description": f"the rigged .fbx or .glb: {_PATH}"},
            "out": {"type": "string",
                    "description": "where to write the roles JSON; must be under output/"},
            "timeout": _TIMEOUT,
        }, ["rig"]),
        "handler": t_bone_roles_map,
    },
    {
        "name": "bone_roles_compile",
        "title": "Compile a role pose for a rig",
        "group": "blender",
        "description":
            "Turn one of the project's role pose files, written in terms of body parts "
            "rather than bone names, into the per-rig transforms file that "
            "render_sprite_sheet reads. This is how a single walk or attack pose is used "
            "on any generated humanoid. Runs Blender in the container and takes a minute "
            "or two.",
        "inputSchema": _obj({
            "role_poses": {"type": "string", "maxLength": 80,
                           "description": "a role pose name the project ships, such as walk, "
                                          "idle, attack or hit"},
            "rig": {"type": "string",
                    "description": f"the rig, or a roles file made by bone_roles_map: {_PATH}"},
            "out": {"type": "string",
                    "description": "where to write the transforms JSON; must be under output/"},
            "feet": {"type": "string", "enum": ["level", "raw"],
                     "description": "level keeps a planted foot flat (the default); raw "
                                    "applies the pose as written"},
            "timeout": _TIMEOUT,
        }, ["role_poses", "rig", "out"]),
        "handler": t_bone_roles_compile,
    },
    {
        "name": "face_rig_add_jaw",
        "title": "Add a jaw bone to a rig",
        "group": "blender",
        "description":
            "Give a generated rig a jaw: one bone, placed under the head and weighted by "
            "rule, so a mouth can be opened for lip sync. Automatic rigs come with no jaw, "
            "eye or mouth bones at all. Writes a .blend or .fbx. Runs Blender in the "
            "container and takes a few minutes. Name the head bone yourself if the "
            "automatic pick is wrong; bone_roles_map tells you which bone that is.",
        "inputSchema": _obj({
            "model": {"type": "string",
                      "description": f"the rigged .fbx, .glb or .blend: {_PATH}"},
            "out": {"type": "string",
                    "description": "the .blend or .fbx to write; must be under output/"},
            "head": {"type": "string", "maxLength": 80,
                     "description": "the head bone, when the automatic pick is wrong"},
            "name": {"type": "string", "maxLength": 80,
                     "description": "name for the new bone (default jaw)"},
            "front": {"type": "string", "enum": ["-y", "+y", "-x", "+x"],
                      "description": "which way the face points in the model's own axes"},
            "timeout": _TIMEOUT,
        }, ["model", "out"]),
        "handler": t_face_rig_add_jaw,
    },
    {
        "name": "decimation_report",
        "title": "Measure what decimation costs a mesh",
        "group": "blender",
        "description":
            "Measure what each face budget costs a model, so the budget is chosen and not "
            "guessed: how far the surface moved, how much of the silhouette survives at "
            "the size the asset is actually seen at, and how far the texture drifted. "
            "Renders from the isometric camera the game uses. TAKES MANY MINUTES: it "
            "decimates and renders the model once per budget, and the default list has "
            "eleven. Give a shorter `faces` list to make it quicker.",
        "inputSchema": _obj({
            "model": {"type": "string",
                      "description": f"the .glb, .gltf, .fbx or .obj: {_PATH}"},
            "faces": {"type": "string", "maxLength": 200,
                      "description": "comma separated face budgets, such as 50000,18000,8000"},
            "sprite": {"type": "integer", "minimum": 16, "maximum": 2048,
                       "description": "the pixel size the silhouette is judged at (default 128)"},
            "target_iou": {"type": "number", "minimum": 0, "maximum": 1,
                           "description": "search for the lowest budget holding this "
                                          "silhouette overlap instead of sweeping the list"},
            "json_out": {"type": "string",
                         "description": "also write the raw numbers here; must be under output/"},
            "timeout": _TIMEOUT,
        }, ["model"]),
        "handler": t_decimation_report,
    },
    {
        "name": "normalise_mesh",
        "title": "Scale a mesh to a world size",
        "group": "blender",
        "description":
            "Scale one or more meshes to a declared world size and record which rule was "
            "applied: `height` for anything that stands, `footprint` for anything sized by "
            "the tile it occupies. Both put the lowest vertex on the ground. This matters "
            "because a sprite sheet frames every model to its own bounding box, so a model "
            "at ten times the intended scale renders perfectly and the error only surfaces "
            "in the game. Set `check` to report without changing anything. Writes a new "
            "file beside each source with a suffix: this server will not overwrite a mesh "
            "in place. Runs Blender in the container and takes minutes.",
        "inputSchema": _obj({
            "models": {"type": "array", "minItems": 1, "maxItems": 50,
                       "items": {"type": "string"},
                       "description": f"the meshes to scale, each {_PATH}"},
            "height": {"type": "number", "minimum": 0.0001, "maximum": 10000,
                       "description": "scale so the Z extent is exactly this"},
            "footprint": {"type": "number", "minimum": 0.0001, "maximum": 10000,
                          "description": "scale so the larger of X and Y is exactly this"},
            "suffix": {"type": "string", "maxLength": 40, "default": "_norm",
                       "description": "appended to each stem (default _norm); an empty "
                                      "suffix is refused unless out_dir is given"},
            "out_dir": {"type": "string",
                        "description": "write here instead of beside each source; under output/"},
            "check": {"type": "boolean", "default": False,
                      "description": "report only, change nothing"},
            "timeout": _TIMEOUT,
        }, ["models"]),
        "handler": t_normalise_mesh,
    },
    {
        "name": "lipsync_cues",
        "title": "Mouth cues for a voice line",
        "group": "lipsync",
        "description":
            "Turn a recorded voice line into mouth cues: which mouth shape is held over "
            "which stretch of the audio, and with `fps` given, one shape per frame at that "
            "rate. A transcript makes the recognition much better, so pass `text` when you "
            "have the line. Point `audio` at one file or at a folder of them. Runs on the "
            "host, not in the container, and takes seconds to a minute per line.",
        "inputSchema": _obj({
            "audio": {"type": "string",
                      "description": f"an audio file, or a folder of them: {_PATH}"},
            "text": {"type": "string", "maxLength": 8000,
                     "description": "the line's transcript, which improves the result"},
            "no_text": {"type": "boolean", "default": False,
                        "description": "no transcript at all, when there is none to give"},
            "out": {"type": "string",
                    "description": "where to write the cue files; must be under output/"},
            "fps": {"type": "number", "minimum": 1, "maximum": 120,
                    "description": "also emit one mouth shape per frame at this rate"},
            "rule": {"type": "string", "enum": ["midpoint", "closure", "share"],
                     "description": "how a frame picks its shape when cues straddle it"},
            "recognizer": {"type": "string", "enum": ["pocketSphinx", "phonetic"],
                           "description": "phonetic for a language the recogniser does not know"},
            "timeout": _TIMEOUT,
        }, ["audio"]),
        "handler": t_lipsync_cues,
    },
    {
        "name": "compose_mouths",
        "title": "Cut mouths out of portrait edits",
        "group": "lipsync",
        "description":
            "Cut the mouth box out of each whole-image edit of a talking portrait and keep "
            "only that, so the hair, lighting and clothes stay exactly the portrait's, and "
            "measure the seam where the pasted mouth meets it. Give the portrait, the "
            "mouth box as X,Y,W,H in its own pixels, and the folder of edited images, one "
            "per shape. Set `check` instead to re-check a manifest that was already "
            "written. Takes seconds.",
        "inputSchema": _obj({
            "portrait": {"type": "string",
                         "description": f"the approved portrait PNG: {_PATH}"},
            "box": {"type": "string", "maxLength": 40,
                    "description": "the mouth box as X,Y,W,H in the portrait's pixels"},
            "edits": {"type": "string",
                      "description": "folder of edited whole images, one per shape"},
            "out": {"type": "string",
                    "description": "where to write the overlays and manifest; under output/"},
            "feather": {"type": "integer", "minimum": 0, "maximum": 200,
                        "description": "soften the box edge by this many pixels"},
            "ring": {"type": "integer", "minimum": 0, "maximum": 200,
                     "description": "width of the ring outside the box the seam is measured in"},
            "check": {"type": "string",
                      "description": "re-check this manifest instead of composing anything"},
            "timeout": _TIMEOUT,
        }),
        "handler": t_compose_mouths,
    },
    {
        "name": "preview_lipsync",
        "title": "Preview a mouth set",
        "group": "lipsync",
        "description":
            "Judge a mouth set the two ways it has to be judged: lay the mouths out on one "
            "labelled contact sheet, so each can be read as its shape, and with a timeline "
            "given, play it as an MP4, so the set can be read as speech. The sheet is a "
            "PNG, which a client can look at; the MP4 is named, not returned. Takes "
            "seconds to a minute.",
        "inputSchema": _obj({
            "manifest": {"type": "string",
                         "description": f"the manifest compose_mouths wrote: {_PATH}"},
            "timeline": {"type": "string",
                         "description": "a cue timeline from lipsync_cues; without it only "
                                        "the contact sheet is made"},
            "audio": {"type": "string", "description": "audio to mux into the MP4"},
            "out": {"type": "string", "description": "the MP4 path; must be under output/"},
            "sheet": {"type": "string", "description": "the contact sheet PNG; under output/"},
            "no_sheet": {"type": "boolean", "default": False,
                         "description": "skip the contact sheet"},
            "label": {"type": "boolean", "default": False,
                      "description": "draw each shape's letter on the frames"},
            "height": {"type": "integer", "minimum": 16, "maximum": 4096,
                       "description": "scale the MP4 to this height"},
            "timeout": _TIMEOUT,
        }, ["manifest"]),
        "handler": t_preview_lipsync,
    },
]

BY_NAME = {t["name"]: t for t in TOOLS}


def public_tools() -> list[dict]:
    """The tool list as a client sees it: no handler, no group."""
    return [{"name": t["name"], "title": t["title"], "description": t["description"],
             "inputSchema": t["inputSchema"]} for t in TOOLS]


# ------------------------------------------------------------------- dispatch

class Session:
    """One client connection. Holds only what the protocol says it must."""

    def __init__(self) -> None:
        self.initialised = False
        self.protocol = PREFERRED_PROTOCOL
        self.client = "unknown"


def rpc_error(msg_id, code: int, message: str, data=None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": error}


def rpc_ok(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def call_tool(name: str, arguments: dict) -> dict:
    tool = BY_NAME.get(name)
    if tool is None:
        near = [n for n in BY_NAME if name.lower() in n.lower() or n.lower() in name.lower()]
        raise LookupError(f"Unknown tool: {name}"
                          + (f". Did you mean {', '.join(near[:3])}?" if near else "")
                          + f" This server has {len(TOOLS)} tools; call tools/list for them.")
    args = validate(tool["inputSchema"], arguments or {}, name)
    try:
        return tool["handler"](args)
    except ToolError as exc:
        return text_result(f"{name} could not run: {exc}", is_error=True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log(f"{name} failed: {type(exc).__name__}: {exc}")
        return text_result(f"{name} failed: {type(exc).__name__}: {exc}", is_error=True)


def handle(message: dict, session: Session):
    """One JSON-RPC message in, one response out, or None for a notification."""
    if message.get("jsonrpc") != "2.0":
        return rpc_error(message.get("id"), INVALID_REQUEST,
                         "Every message must carry \"jsonrpc\": \"2.0\"")
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}
    if not isinstance(method, str):
        return rpc_error(msg_id, INVALID_REQUEST, "A request must carry a string \"method\"")
    if not isinstance(params, dict):
        return rpc_error(msg_id, INVALID_PARAMS, "\"params\" must be an object")

    if msg_id is None:                                     # a notification
        if method == "notifications/initialized":
            session.initialised = True
            log(f"initialised by {session.client}, protocol {session.protocol}")
        elif method == "notifications/cancelled":
            log(f"client cancelled request {params.get('requestId')}")
        else:
            log(f"ignoring unknown notification {method}")
        return None

    if method == "initialize":
        wanted = params.get("protocolVersion")
        session.protocol = wanted if wanted in PROTOCOL_VERSIONS else PREFERRED_PROTOCOL
        info = params.get("clientInfo") or {}
        session.client = f"{info.get('name', '?')} {info.get('version', '?')}".strip()
        if wanted and wanted not in PROTOCOL_VERSIONS:
            log(f"client asked for protocol {wanted}, offering {PREFERRED_PROTOCOL}")
        return rpc_ok(msg_id, {
            "protocolVersion": session.protocol,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "title": "Game asset engine",
                           "version": SERVER_VERSION},
            "instructions":
                "Tools for a game asset pipeline: 3D and 2D generation, Blender rigging "
                "and sprite sheets, and lip sync. Call engine_health first when anything "
                "fails, and queue_status before queueing generation or Blender work, "
                "because the server and the graphics card are shared. Generation and "
                "Blender tools take minutes. Nothing here deletes, uninstalls or "
                "publishes, and every path must lie under output/, input/ or the models "
                "directory.",
        })

    if method == "server/discover":
        # The current specification revision probes with this before falling back
        # to the initialize handshake. Answering it honestly, with only the
        # handshake revisions, is what makes that fallback happen.
        return rpc_ok(msg_id, {
            "supportedVersions": list(PROTOCOL_VERSIONS),
            "capabilities": {"tools": {"listChanged": False}},
            "_meta": {"io.modelcontextprotocol/serverInfo":
                      {"name": SERVER_NAME, "version": SERVER_VERSION}},
            "instructions": "This server speaks the initialize-handshake revisions of "
                            "MCP. Send initialize with one of supportedVersions.",
        })

    if method == "ping":
        return rpc_ok(msg_id, {})

    if method == "tools/list":
        return rpc_ok(msg_id, {"tools": public_tools()})

    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return rpc_error(msg_id, INVALID_PARAMS,
                             "tools/call needs a string \"name\"; call tools/list for them")
        arguments = params.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return rpc_error(msg_id, INVALID_PARAMS, "\"arguments\" must be an object")
        try:
            return rpc_ok(msg_id, call_tool(name, arguments))
        except LookupError as exc:
            return rpc_error(msg_id, INVALID_PARAMS, str(exc))
        except ToolError as exc:
            return rpc_error(msg_id, INVALID_PARAMS, str(exc))
        except Exception as exc:                      # never let a traceback out
            log(f"tools/call {name} raised {type(exc).__name__}: {exc}")
            return rpc_error(msg_id, INTERNAL_ERROR,
                             f"{name} failed inside the server: {type(exc).__name__}: {exc}")

    known = ("initialize", "server/discover", "ping", "tools/list", "tools/call")
    return rpc_error(msg_id, METHOD_NOT_FOUND,
                     f"This server does not implement {method}. It implements "
                     + ", ".join(known)
                     + ". It offers no resources, prompts, sampling, completions or logging.")


def handle_frame(raw: str, session: Session) -> dict | None:
    try:
        message = json.loads(raw)
    except ValueError as exc:
        return rpc_error(None, PARSE_ERROR, f"Not valid JSON: {exc}")
    if isinstance(message, list):
        return rpc_error(None, INVALID_REQUEST,
                         "Batched requests are not supported; send one message per frame")
    if not isinstance(message, dict):
        return rpc_error(None, INVALID_REQUEST, "A JSON-RPC message must be an object")
    return handle(message, session)


# --------------------------------------------------------------------- stdio

def serve_stdio() -> int:
    session = Session()
    out = sys.stdout

    def bye(signum, _frame):
        log(f"signal {signum}, shutting down")
        raise SystemExit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, bye)
        except ValueError:
            pass
    log(f"stdio, repo {REPO}, {len(TOOLS)} tools, protocol {PREFERRED_PROTOCOL}")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = handle_frame(line, session)
            if response is not None:
                out.write(json.dumps(response) + "\n")
                out.flush()
    except SystemExit:
        return 0
    except KeyboardInterrupt:
        return 0
    log("stdin closed, shutting down")
    return 0


# ---------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = f"{SERVER_NAME}/{SERVER_VERSION}"
    session: Session

    def log_message(self, fmt, *args):                      # stderr, not stdout
        log("http " + (fmt % args))

    def _send(self, status: int, payload: dict | None, extra: dict | None = None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        if body:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
        self.send_header("MCP-Protocol-Version", self.session.protocol)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        self._send(405, rpc_error(None, METHOD_NOT_FOUND,
                                  "This server answers POST only. It does not implement "
                                  "server-sent events, resumable streams or sessions."),
                   {"Allow": "POST"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 4 * 1024 * 1024:
            self._send(413, rpc_error(None, INVALID_REQUEST, "Request body too large"))
            return
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        response = handle_frame(raw or "{}", self.session)
        if response is None:
            self._send(202, None)
        else:
            self._send(200, response)


def serve_http(host: str, port: int) -> int:
    Handler.session = Session()
    httpd = ThreadingHTTPServer((host, port), Handler)
    log(f"http on {host}:{port}, repo {REPO}, {len(TOOLS)} tools")
    if host not in ("127.0.0.1", "localhost", "::1"):
        log("WARNING: this is plain HTTP with no authentication of its own. The MCP "
            "specification requires https for a remote transport, so put a reverse proxy "
            "in front of it that terminates TLS and checks authorisation.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("interrupted, shutting down")
    finally:
        httpd.server_close()
    return 0


# ------------------------------------------------------------------- selftest

def selftest() -> int:
    """Start this server as a child, speak the protocol to it, check the replies."""
    here = Path(__file__).resolve()
    argv = [sys.executable, str(here)]
    log("selftest: starting a child server on a pipe")
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, bufsize=1,
                             cwd=str(REPO), env=os.environ.copy())
    failures: list[str] = []
    checks = 0

    def send(message: dict):
        child.stdin.write(json.dumps(message) + "\n")
        child.stdin.flush()

    def read(timeout: float = 240.0) -> dict:
        box: list[str] = []

        def pull():
            line = child.stdout.readline()
            box.append(line)

        thread = threading.Thread(target=pull, daemon=True)
        thread.start()
        thread.join(timeout)
        if not box:
            raise TimeoutError(f"no reply within {timeout:.0f}s")
        if not box[0]:
            raise EOFError("the server closed its output")
        return json.loads(box[0])

    def check(label: str, condition: bool, detail: str = ""):
        nonlocal checks
        checks += 1
        if condition:
            print(f"  ok    {label}")
        else:
            print(f"  FAIL  {label}  {detail}")
            failures.append(label)

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": PREFERRED_PROTOCOL, "capabilities": {},
                         "clientInfo": {"name": "asset-engine-selftest", "version": "1"}}})
        reply = read(30)
        result = reply.get("result", {})
        check("initialize returns the negotiated protocol version",
              result.get("protocolVersion") == PREFERRED_PROTOCOL, repr(reply)[:200])
        check("initialize names the server and its version",
              result.get("serverInfo", {}).get("name") == SERVER_NAME
              and bool(result.get("serverInfo", {}).get("version")), repr(result)[:200])
        check("initialize declares the tools capability",
              "tools" in result.get("capabilities", {}), repr(result)[:200])

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        check("ping answers with an empty result", read(30).get("result") == {}, "")

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        listed = read(30).get("result", {}).get("tools", [])
        check(f"tools/list returns all {len(TOOLS)} tools", len(listed) == len(TOOLS),
              f"got {len(listed)}")
        check("every tool has a name, a description and an object input schema",
              all(t.get("name") and len(t.get("description", "")) > 40
                  and t.get("inputSchema", {}).get("type") == "object" for t in listed))

        send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
              "params": {"name": "list_graphs", "arguments": {}}})
        body = read(60).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("list_graphs lists the API graphs",
              not body.get("isError") and "txt2img_sdxl" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
              "params": {"name": "list_models", "arguments": {"mode": "groups"}}})
        body = read(120).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("list_models lists the model groups",
              not body.get("isError") and "core" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
              "params": {"name": "list_prompt_folders", "arguments": {}}})
        body = read(60).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("list_prompt_folders lists the prompt folders",
              not body.get("isError") and "creatures" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
              "params": {"name": "list_assets", "arguments": {}}})
        body = read(60).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("list_assets lists the curated assets",
              not body.get("isError") and "curated assets" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 8, "method": "tools/call",
              "params": {"name": "queue_status", "arguments": {}}})
        body = read(60).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("queue_status reports the running and pending counts",
              "running:" in text and "pending:" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
              "params": {"name": "engine_health", "arguments": {"format": "json"}}})
        body = read(300).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("engine_health returns a report", "doctor.py --skip-models" in text, text[:200])

        # The refusals. Each must be a message, never a traceback.
        send({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
              "params": {"name": "inspect_sprite_sheet",
                         "arguments": {"sheet": "/etc/passwd", "cell": 64}}})
        body = read(30).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("a path outside the allowed folders is refused",
              body.get("isError") and "outside the folders" in text, text[:200])

        send({"jsonrpc": "2.0", "id": 11, "method": "tools/call",
              "params": {"name": "inspect_sprite_sheet",
                         "arguments": {"sheet": "output/sheets/x.png", "cell": "big"}}})
        reply = read(30)
        check("a badly typed argument is a JSON-RPC error, not a crash",
              reply.get("error", {}).get("code") == INVALID_PARAMS
              and "expected integer" in reply.get("error", {}).get("message", ""),
              repr(reply)[:200])

        send({"jsonrpc": "2.0", "id": 12, "method": "tools/call",
              "params": {"name": "no_such_tool", "arguments": {}}})
        reply = read(30)
        check("an unknown tool is a JSON-RPC error",
              reply.get("error", {}).get("code") == INVALID_PARAMS
              and "Unknown tool" in reply.get("error", {}).get("message", ""),
              repr(reply)[:200])

        send({"jsonrpc": "2.0", "id": 13, "method": "resources/list"})
        reply = read(30)
        check("an unimplemented method is error -32601",
              reply.get("error", {}).get("code") == METHOD_NOT_FOUND, repr(reply)[:200])

        child.stdin.write("this is not json\n")
        child.stdin.flush()
        reply = read(30)
        check("a malformed frame is error -32700",
              reply.get("error", {}).get("code") == PARSE_ERROR, repr(reply)[:200])

        send({"jsonrpc": "2.0", "id": 14, "method": "tools/call",
              "params": {"name": "run_graph",
                         "arguments": {"graph": "txt2img_sdxl", "subject": "a",
                                       "prompt": "b", "dry_run": True}}})
        body = read(60).get("result", {})
        text = "".join(c.get("text", "") for c in body.get("content", []))
        check("run_graph refuses subject and prompt together, before queueing anything",
              body.get("isError") and "not both" in text, text[:200])

        # Clean shutdown: close stdin and the server should exit 0 by itself.
        child.stdin.close()
        try:
            code = child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            code = None
        check("closing stdin shuts the server down with exit 0", code == 0, f"exit {code}")
    except (TimeoutError, EOFError, ValueError) as exc:
        print(f"  FAIL  the conversation broke: {type(exc).__name__}: {exc}")
        failures.append("conversation")
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
        stderr = (child.stderr.read() or "") if child.stderr else ""
        if stderr.strip():
            print("\nthe server's stderr:")
            for line in stderr.strip().splitlines()[-25:]:
                print(f"  {line}")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    if failures:
        print("failed: " + ", ".join(failures))
        return 1
    return 0


# ------------------------------------------------------------------ the front

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--http", action="store_true",
                    help="serve over HTTP instead of stdio; no authentication of its own")
    ap.add_argument("--host", default="127.0.0.1",
                    help="HTTP bind address (default 127.0.0.1; anything else needs a "
                         "TLS reverse proxy in front)")
    ap.add_argument("--port", type=int, default=8765, help="HTTP port (default 8765)")
    ap.add_argument("--selftest", action="store_true",
                    help="start a copy of this server, speak the protocol to it over a "
                         "pipe, call read-only tools and check the replies")
    ap.add_argument("--list-tools", action="store_true",
                    help="print the tools and the first line of each description")
    args = ap.parse_args(argv)

    if args.list_tools:
        for group in ("read-only", "queue", "blender", "lipsync"):
            print(f"\n{group}:")
            for tool in TOOLS:
                if tool["group"] != group:
                    continue
                first = tool["description"].split(". ")[0]
                print(f"  {tool['name']:<22} {first}.")
        print(f"\n{len(TOOLS)} tools. Repository root: {REPO}")
        return 0
    if args.selftest:
        return selftest()
    if args.http:
        return serve_http(args.host, args.port)
    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main())
