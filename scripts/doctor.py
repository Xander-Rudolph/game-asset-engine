#!/usr/bin/env python3
"""Check that the asset engine can actually run, and say what to do if it cannot.

    scripts/doctor.py            # check everything, print what is wrong
    scripts/doctor.py --fix      # also do the safe fixes (write .env, start it)
    scripts/doctor.py --quiet    # exit code only, for scripts
    scripts/doctor.py --json     # machine-readable, for skills

Every skill in this repo runs this first. The reason is narrow and practical:
almost every confusing failure in this pipeline is one of six ordinary things
(no Docker, no GPU, no .env, no image, container down, weights missing), and
each of them shows up much later as something that looks like a broken
workflow. Checking takes two seconds and removes the guessing.

Exit codes: 0 everything ready, 1 something is missing, 2 could not check.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container as _container  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def container() -> str:
    """The running container's name, resolved fresh every time.

    NOT cached at import. --fix starts a container partway through the run, so
    a name resolved before that is the name of something that does not exist
    yet -- and every later `docker exec` against it fails. That produced a
    confident "bpy is not importable", which is a fault that reads as a broken
    image and invites a 27GB rebuild to fix nothing.
    """
    return _container()
URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
IMAGE = os.environ.get("ATHANOR_COMFY_IMAGE_REPO", "ghcr.io/athanorgames/athanor-comfy")

# Node classes the shipped workflows need. A missing one means the pack did not
# load, which the server reports only in its startup log.
NEEDED_NODES = {
    "[Comfy3D] Load 3D Mesh": "ComfyUI-3D-Pack",
    "[Comfy3D] Save 3D Mesh": "ComfyUI-3D-Pack",
    "UniRigAutoRig": "ComfyUI-UniRig",
}

OK, WARN, BAD = "ok", "warn", "bad"
MARK = {OK: "  ok  ", WARN: " warn ", BAD: " MISS "}


class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, state: str, name: str, detail: str = "", fix: str = "") -> str:
        self.rows.append({"state": state, "check": name, "detail": detail, "fix": fix})
        return state

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.rows if r["state"] == BAD]


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def http(path: str, timeout: int = 5) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f"{URL}{path}", timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # connection refused, DNS, timeout
        return 0, str(e)


def check_docker(rep: Report) -> bool:
    if not shutil.which("docker"):
        rep.add(BAD, "docker", "the docker command is not on PATH",
                "Install Docker Engine, then add yourself to the docker group: "
                "sudo usermod -aG docker $USER (log out and back in)")
        return False
    code, out = run(["docker", "info", "--format", "{{.ServerVersion}}"])
    if code != 0:
        rep.add(BAD, "docker", "the daemon did not answer",
                "sudo systemctl start docker  (or check you are in the docker group)")
        return False
    rep.add(OK, "docker", f"engine {out.splitlines()[0] if out else '?'}")
    return True


def check_gpu(rep: Report) -> None:
    code, out = run(["docker", "info", "--format", "{{json .Runtimes}}"])
    if code == 0 and "nvidia" in out:
        rep.add(OK, "gpu runtime", "nvidia runtime registered with docker")
        return
    if shutil.which("nvidia-smi"):
        rep.add(WARN, "gpu runtime",
                "an NVIDIA card is present but docker has no nvidia runtime",
                "Install the NVIDIA Container Toolkit, then: "
                "sudo nvidia-ctk runtime configure --runtime=docker && "
                "sudo systemctl restart docker")
    else:
        rep.add(WARN, "gpu runtime", "no NVIDIA GPU found",
                "The pipeline runs on CPU only in theory. In practice mesh "
                "generation needs a CUDA GPU with 12GB or more.")


def check_env(rep: Report, fix: bool) -> None:
    env = ROOT / ".env"
    if env.exists():
        text = env.read_text()
        models = next((l.split("=", 1)[1].strip() for l in text.splitlines()
                       if l.startswith("MODELS_DIR=")), "")
        rep.add(OK, ".env", f"MODELS_DIR={models or 'unset'}")
        return
    if fix and (ROOT / ".env.example").exists():
        shutil.copy(ROOT / ".env.example", env)
        rep.add(WARN, ".env", "written from .env.example",
                "Open .env and set MODELS_DIR to where the weights live")
        return
    rep.add(BAD, ".env", "missing", "cp .env.example .env, then set MODELS_DIR")


def check_image(rep: Report) -> bool:
    code, out = run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
    if code != 0:
        rep.add(BAD, "image", "could not list images", "")
        return False
    tags = [t for t in out.splitlines() if IMAGE in t or "comfyui" in t]
    if tags:
        rep.add(OK, "image", ", ".join(tags[:3]))
        return True
    rep.add(BAD, "image", "no ComfyUI image built or pulled",
            f"docker pull {IMAGE}:latest   (27GB), then "
            "docker compose --profile packaged up -d")
    return False


def check_container(rep: Report, fix: bool) -> bool:
    name = container()
    code, out = run(["docker", "ps", "--filter", f"name=^{name}$",
                     "--format", "{{.Status}}"])
    if code == 0 and out:
        rep.add(OK, "container", f"{name} is {out.splitlines()[0].lower()}")
        return True
    code, out = run(["docker", "ps", "-a", "--filter", f"name=^{name}$",
                     "--format", "{{.Status}}"])
    exists = bool(out)
    if fix:
        profile = "packaged" if _packaged() else "comfy"
        c, o = run(["docker", "compose", "--profile", profile, "up", "-d"], timeout=180)
        if c == 0:
            rep.add(WARN, "container", f"started with profile {profile}")
            return True
        rep.add(BAD, "container", f"could not start it: {o[-300:]}", "")
        return False
    rep.add(BAD, "container",
            f"{name} exists but is stopped" if exists else f"{name} is not running",
            "docker compose --profile packaged up -d   (or --profile comfy if you "
            "build from source)")
    return False


def _packaged() -> bool:
    """Prefer the packaged profile when the published image is the one on disk."""
    _, out = run(["docker", "images", "--format", "{{.Repository}}"])
    return IMAGE in out


def check_server(rep: Report, fix: bool) -> dict | None:
    deadline = time.time() + (180 if fix else 0)
    while True:
        status, body = http("/object_info")
        if status == 200:
            try:
                info = json.loads(body)
            except json.JSONDecodeError:
                rep.add(BAD, "server", "/object_info was not JSON", "")
                return None
            rep.add(OK, "server", f"{URL} answering, {len(info)} node types loaded")
            return info
        if time.time() >= deadline:
            break
        time.sleep(4)
    rep.add(BAD, "server", f"nothing answering at {URL}",
            "The container can be up while ComfyUI is still importing nodes, which "
            "takes a minute or two on a cold start. Watch it: "
            f"docker logs -f {container()}")
    return None


def check_nodes(rep: Report, info: dict) -> None:
    missing = {n: pack for n, pack in NEEDED_NODES.items() if n not in info}
    if not missing:
        rep.add(OK, "node packs", "3D-Pack and UniRig both loaded")
        return
    packs = sorted(set(missing.values()))
    rep.add(BAD, "node packs", f"not loaded: {', '.join(packs)}",
            f"docker logs {container()} 2>&1 | grep -i -A5 'error\\|traceback' | head -40  "
            "(a node pack that fails to import says why there, and nowhere else)")


def check_blender(rep: Report) -> None:
    code, out = run(["docker", "exec", container(), "python3", "-c",
                     "import bpy; print(bpy.app.version_string)"], timeout=120)
    if code == 0 and out:
        rep.add(OK, "blender", f"bpy {out.strip().splitlines()[-1]} in the container")
    else:
        rep.add(BAD, "blender", f"bpy is not importable in {container()}",
                "Sprite sheets, posing, decimation reports and weight transfer all "
                "run through Blender inside the container. Check the container is "
                "the one you think it is before rebuilding anything: "
                f"docker exec {container()} python3 -c 'import bpy'")


def check_models(rep: Report) -> None:
    script = ROOT / "scripts" / "fetch_models.py"
    if not script.exists():
        return
    code, out = run([sys.executable, str(script)], timeout=120)
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    if code == 0 and "missing" not in out.lower():
        rep.add(OK, "weights", tail[:90] or "core group present")
    else:
        rep.add(WARN, "weights", tail[:90] or "some weights are missing",
                "scripts/fetch_models.py --download   (core is about 21GB)")


def check_writable(rep: Report) -> None:
    bad = []
    for d in ("output", "input", "logs"):
        p = ROOT / d
        p.mkdir(exist_ok=True)
        if not os.access(p, os.W_OK):
            bad.append(d)
    if bad:
        rep.add(WARN, "folders", f"not writable by you: {', '.join(bad)}",
                "Set PUID and PGID in .env to your own id -u and id -g, then "
                "recreate the container. Otherwise output lands owned by root.")
    else:
        rep.add(OK, "folders", "output, input and logs are writable")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true",
                    help="do the safe fixes: write .env, start the container, wait for it")
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--skip-models", action="store_true",
                    help="skip the weight check, which is the slow one")
    args = ap.parse_args()

    rep = Report()
    if check_docker(rep):
        check_gpu(rep)
        check_env(rep, args.fix)
        have_image = check_image(rep)
        up = check_container(rep, args.fix) if have_image else False
        info = check_server(rep, args.fix) if up else None
        if info:
            check_nodes(rep, info)
            check_blender(rep)
        if not args.skip_models:
            check_models(rep)
        check_writable(rep)

    if args.json:
        print(json.dumps({"ready": not rep.failed, "checks": rep.rows}, indent=2))
    elif not args.quiet:
        print()
        for r in rep.rows:
            print(f"  [{MARK[r['state']]}] {r['check']:<12} {r['detail']}")
        print()
        first = rep.failed[0] if rep.failed else None
        if first and first["fix"]:
            print("  Next step:")
            for line in first["fix"].split("  "):
                if line.strip():
                    print(f"    {line.strip()}")
            print()
        elif not rep.failed:
            hints = [r for r in rep.rows if r["state"] == WARN and r["fix"]]
            print("  Ready. " + ("Worth doing:" if hints else "Nothing to fix."))
            for h in hints:
                print(f"    {h['check']}: {h['fix']}")
            print()
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
