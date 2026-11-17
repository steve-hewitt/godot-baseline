#!/usr/bin/env python3
# =============================================================================
# godot-baseline setup script -- runs INSIDE WSL (Ubuntu) and installs
# the baseline: system packages, GitHub CLI, uv + Python, Node, Bun,
# Beads, Godot (headless), OpenCode, and a starter Godot project.
# GUIDE.md starts this script with one typed line from the Windows side
# (there is no Windows-side script in this kit); it can also be run by hand.
#
# Rules this script lives by:
#   * Standard library only. It must run on the Python 3 that a stock
#     Ubuntu ships, before anything else is installed.
#   * Check before acting. Every step first checks whether its work is
#     already done at the pinned version, and skips if so. Re-running
#     this script is always safe, including after a reboot or a failure.
#   * Plain language on screen. Technical detail goes to the log file.
#   * Never overwrite a user's existing config. The OpenCode config is
#     created only if absent, and only the model key is added if the
#     file exists without one.
#
# Verbs:
#   install    install or finish installing everything
#   doctor     check everything, print the tick list, write a report
#   repair     like install, but re-installs anything at a wrong version
#   uninstall  remove the tools this script installed (projects stay)
#
# Flags:
#   --dry-run     print what would happen, change nothing
#   --skip-apt    skip the sudo apt step (testing)
#   --skip-auth   skip the interactive sign-in pauses (testing)
#   --skip-starter skip the starter project step (testing)
# =============================================================================

import argparse
import hashlib
import inspect
import json
import os
import platform
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

# ---------------------------------------------------------------------------
# Pins. One place, on purpose. Current latest of each, checked upstream
# on 2026-11-16. See docs/DESIGN.md.
# ---------------------------------------------------------------------------
PIN_BD = "1.3.4"
PIN_GH = "2.104.0"
PIN_UV = "0.13.8"
PIN_PYTHON = "3.15.2"
PIN_NODE = "26.13.1"
PIN_NODE_SHA256_X64 = "5c063e46bab0fbc1c17cc445d7ff129cbdcd0471be6ed83b6ab864f8143bc864"
PIN_BUN = "1.4.4"
PIN_GODOT = "4.7.2"
PIN_OPENCODE = "2.3.0"
# Default model for OpenCode: Big Pickle, free on OpenCode Zen. Verified
# against the live Zen roster (models.dev) on 2026-11-16: $0 in/out, 200K
# context, 32K output, tool calls supported. Free Zen lanes are
# promotional, so if this one ever disappears, this constant is the one
# line to change.
DEFAULT_MODEL = "opencode/big-pickle"

STARTER_NAME = "my-first-game"

HOME = os.path.expanduser("~")
LOCAL_BIN = os.path.join(HOME, ".local", "bin")
OPT_DIR = os.path.join(HOME, ".local", "opt")
STATE_DIR = os.path.join(HOME, ".local", "state", "godot-baseline")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LOG_FILE = os.path.join(STATE_DIR, "setup.log")
DL_DIR = os.path.join(STATE_DIR, "downloads")
VENV_DIR = os.path.join(HOME, ".venvs", "baseline")
STARTER_DIR = os.path.join(HOME, STARTER_NAME)
REPORT_FILE = os.path.join(HOME, "godot-baseline-report.txt")
ISSUES_URL = "https://github.com/steve-hewitt/godot-baseline/issues"
OPENCODE_CONFIG = os.path.join(HOME, ".config", "opencode", "opencode.json")

MACHINE = platform.machine()
ARCH_GH = {"x86_64": "amd64", "aarch64": "arm64"}.get(MACHINE, "amd64")
ARCH_NODE = {"x86_64": "x64", "aarch64": "arm64"}.get(MACHINE, "x64")
ARCH_GODOT = {"x86_64": "x86_64", "aarch64": "arm64"}.get(MACHINE, "x86_64")
ARCH_UV = {"x86_64": "x86_64-unknown-linux-gnu",
           "aarch64": "aarch64-unknown-linux-gnu"}.get(MACHINE, "x86_64-unknown-linux-gnu")
ARCH_BUN = {"x86_64": "x64", "aarch64": "arm64"}.get(MACHINE, "x64")

DRY_RUN = False
LOG_FH = None


class StepError(Exception):
    """A step failed. The message is plain language for the user."""


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    if LOG_FH:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def say(msg=""):
    print(msg, flush=True)
    log("SAY: " + msg)


def load_state():
    try:
        with open(STATE_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {"steps": {}, "created": {}}


def save_state(state):
    if DRY_RUN:
        return
    os.makedirs(STATE_DIR, exist_ok=True)
    existing = load_state()
    created = dict(existing.get("created", {}))
    created.update(state.get("created", {}))
    created_paths = list(existing.get("created", {}).get("paths", []))
    for path in state.get("created", {}).get("paths", []):
        if path not in created_paths:
            created_paths.append(path)
    if created_paths:
        created["paths"] = created_paths
    state["created"] = created
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, STATE_FILE)


def record_created_path(path):
    state = load_state()
    paths = state.setdefault("created", {}).setdefault("paths", [])
    path = os.path.abspath(path)
    if path not in paths:
        paths.append(path)
        save_state(state)


def path_is_owned(path):
    path = os.path.abspath(path)
    return path in load_state().get("created", {}).get("paths", [])


def venv_python_version():
    config = os.path.join(VENV_DIR, "pyvenv.cfg")
    if not os.path.isfile(os.path.join(VENV_DIR, "bin", "python")):
        return None
    try:
        with open(config) as fh:
            for line in fh:
                match = re.match(r"\s*version\s*=\s*(\d+\.\d+\.\d+)\s*$", line)
                if match:
                    return match.group(1)
    except OSError:
        return None
    return None


def remove_owned_path(path):
    if not path_is_owned(path):
        raise StepError("An existing file was not created by this setup and was left untouched: %s" % path)
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def run(cmd, inherit=False, timeout=1200, env_extra=None):
    """Run a command. Output goes to the log; with inherit=True the user
    sees and can answer the command directly (sign-ins, sudo)."""
    log("RUN: " + " ".join(cmd))
    if DRY_RUN:
        say("  (dry run) would run: " + " ".join(cmd))
        return 0, ""
    env = dict(os.environ)
    env["PATH"] = LOCAL_BIN + os.pathsep + env.get("PATH", "")
    if env_extra:
        env.update(env_extra)
    if inherit:
        proc = subprocess.run(cmd, env=env, timeout=timeout)
        return proc.returncode, ""
    proc = subprocess.run(cmd, env=env, timeout=timeout,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    if proc.stdout:
        log("OUT: " + proc.stdout[-4000:])
    return proc.returncode, proc.stdout or ""


def sh(command, timeout=120):
    """Run a shell command in a login shell, so PATH is what the user's
    own terminal would see. Returns (exit_code, output)."""
    return run(["bash", "-lc", command], timeout=timeout)


def have(tool):
    code, _ = sh("command -v %s" % tool, timeout=30)
    return code == 0


def version_of(tool, args=("--version",)):
    code, out = sh("%s %s" % (tool, " ".join(args)), timeout=30)
    if code != 0:
        return None
    match = re.search(r"(\d+\.\d+\.\d+)", out)
    return match.group(1) if match else None


def download(url, dest, tries=3):
    """Download with retries. Prints a simple progress line."""
    if DRY_RUN:
        say("  (dry run) would download: " + url)
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "godot-baseline"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = resp.read(1 << 18)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = int(done * 100 / total)
                        sys.stdout.write("\r  downloading... %d%%" % pct)
                        sys.stdout.flush()
                sys.stdout.write("\r  downloading... done.   \n")
                sys.stdout.flush()
            return dest
        except Exception as err:  # noqa: BLE001 - report and retry
            last_err = err
            log("download failed (%s): %s" % (attempt, err))
            time.sleep(2)
    raise StepError("A download failed after %d tries: %s\n  %s" % (tries, url, last_err))


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "godot-baseline"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def hash_of(path, algo):
    digest = hashlib.new(algo)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_from_sums(sums_text, filename, path, algo):
    """Check a file against a sums file (lines of '<hash>  <name>')."""
    for line in sums_text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename:
            expected = parts[0].lower()
            actual = hash_of(path, algo)
            if actual.lower() != expected:
                raise StepError("A downloaded file did not match its official checksum: %s" % filename)
            log("checksum ok: %s" % filename)
            return True
    raise StepError("The official checksum list did not contain %s" % filename)


def install_file(src, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if DRY_RUN:
        say("  (dry run) would install %s -> %s" % (src, dest))
        return
    if os.path.lexists(dest):
        remove_owned_path(dest)
    shutil.copy2(src, dest)
    os.chmod(dest, 0o755)
    record_created_path(dest)
    log("installed %s" % dest)


def link_into_bin(target, name=None):
    dest = os.path.join(LOCAL_BIN, name or os.path.basename(target))
    if DRY_RUN:
        say("  (dry run) would link %s" % dest)
        return
    os.makedirs(LOCAL_BIN, exist_ok=True)
    if os.path.lexists(dest):
        if os.path.islink(dest) and os.path.realpath(dest) == os.path.realpath(target):
            return
        remove_owned_path(dest)
    os.symlink(target, dest)
    record_created_path(dest)
    log("linked %s -> %s" % (dest, target))


def extract_tar(path, dest_dir):
    with tarfile.open(path) as tar:
        if "filter" in inspect.signature(tarfile.TarFile.extractall).parameters:
            tar.extractall(dest_dir, filter="data")
            return
        root = os.path.abspath(dest_dir)
        members = tar.getmembers()
        for member in members:
            name = member.name
            destination = os.path.abspath(os.path.join(root, name))
            if os.path.isabs(name) or os.path.commonpath((root, destination)) != root:
                raise StepError("The downloaded archive contains an unsafe path: %s" % name)
            if member.issym() or member.islnk():
                linkname = member.linkname
                if os.path.isabs(linkname):
                    raise StepError("The downloaded archive contains an unsafe link: %s" % name)
                base = posixpath.dirname(name) if member.issym() else ""
                link_target = posixpath.normpath(posixpath.join(base, linkname))
                if link_target == ".." or link_target.startswith("../"):
                    raise StepError("The downloaded archive contains an unsafe link: %s" % name)
            elif not (member.isdir() or member.isfile()):
                raise StepError("The downloaded archive contains an unsupported file: %s" % name)
        tar.extractall(dest_dir, members=members)


def extract_zip(path, dest_dir):
    with zipfile.ZipFile(path) as zf:
        zf.extractall(dest_dir)


def find_file(root, name):
    for dirpath, _dirnames, filenames in os.walk(root):
        if name in filenames:
            return os.path.join(dirpath, name)
    return None


def ensure_path_block():
    """Make sure ~/.local/bin is first on PATH in the user's shells."""
    block = ('# >>> godot-baseline >>>\n'
             'export PATH="$HOME/.local/bin:$PATH"\n'
             '# <<< godot-baseline <<<\n')
    for rc_name in (".bashrc", ".profile"):
        rc_path = os.path.join(HOME, rc_name)
        try:
            with open(rc_path) as fh:
                content = fh.read()
        except Exception:
            content = ""
        if "godot-baseline >>>" in content:
            continue
        if DRY_RUN:
            say("  (dry run) would add the PATH block to %s" % rc_path)
            continue
        with open(rc_path, "a") as fh:
            fh.write("\n" + block)
        log("PATH block added to %s" % rc_path)


def sudo_refresh():
    code, _ = run(["sudo", "-v"], inherit=True, timeout=120)
    if code != 0:
        raise StepError("The password step did not finish, so installs that need it cannot run.")


# ---------------------------------------------------------------------------
# Steps. Each returns True when its work is in place. Hard failures raise
# StepError with a plain-language message.
# ---------------------------------------------------------------------------

APT_PACKAGES = ["git", "jq", "curl", "ripgrep", "unzip", "ca-certificates"]
APT_TOOLS = {"git": "git", "jq": "jq", "curl": "curl",
             "ripgrep": "rg", "unzip": "unzip"}


def step_apt():
    missing = [pkg for pkg, tool in APT_TOOLS.items() if not have(tool)]
    if not missing:
        return True
    say("Installing basic tools (git, jq, curl, ripgrep, unzip).")
    say("Your Ubuntu password is needed for this. Nothing shows while you type. That is normal.")
    sudo_refresh()
    code, _ = run(["sudo", "apt-get", "update"], timeout=900)
    if code != 0:
        raise StepError("Ubuntu could not refresh its package list. Check the internet connection and run me again.")
    sudo_refresh()
    code, _ = run(["sudo", "apt-get", "install", "-y"] + APT_PACKAGES, timeout=1800)
    if code != 0:
        raise StepError("Ubuntu could not install the basic tools. Run me again; finished parts are skipped.")
    if DRY_RUN:
        return True
    still = [pkg for pkg, tool in APT_TOOLS.items() if not have(tool)]
    if still:
        raise StepError("These tools are still missing after install: %s" % ", ".join(still))
    return True


def step_gh():
    if version_of("gh") == PIN_GH:
        return True
    say("Installing the GitHub tool (gh) %s." % PIN_GH)
    name = "gh_%s_linux_%s.tar.gz" % (PIN_GH, ARCH_GH)
    base = "https://github.com/cli/cli/releases/download/v%s/" % PIN_GH
    archive = download(base + name, os.path.join(DL_DIR, name))
    if DRY_RUN:
        return True
    sums = fetch_text(base + "gh_%s_checksums.txt" % PIN_GH)
    verify_from_sums(sums, name, archive, "sha256")
    work = os.path.join(DL_DIR, "gh-extract")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    extract_tar(archive, work)
    binary = find_file(work, "gh")
    if not binary:
        raise StepError("The GitHub download did not contain the gh program.")
    install_file(binary, os.path.join(LOCAL_BIN, "gh"))
    if DRY_RUN:
        return True
    if version_of("gh") != PIN_GH:
        raise StepError("gh installed but does not report version %s." % PIN_GH)
    return True


def step_gh_auth(skip_auth):
    code, _ = sh("gh auth status", timeout=60)
    if code == 0:
        _git_identity()
        return True
    if skip_auth:
        say("Skipping the GitHub sign-in (testing mode).")
        return True
    say("")
    say("STEP: Sign in to GitHub.")
    say("This sets the git name and email on this machine.")
    say("1. If you have no GitHub account, the page that opens lets you make one.")
    say("2. Type the code you are shown into the browser page, and approve.")
    say("Press Enter when you are ready.")
    if not DRY_RUN:
        input()
    code, _ = run(["gh", "auth", "login", "--hostname", "github.com",
                   "--git-protocol", "https", "--web"], inherit=True, timeout=1800)
    if code != 0:
        raise StepError("The GitHub sign-in did not finish. Run me again and it will pick up here.")
    run(["gh", "auth", "setup-git"], timeout=60)
    _git_identity()
    return True


def _git_identity():
    code, out = run(["gh", "api", "user"], timeout=60)
    if code != 0:
        log("could not read the GitHub profile; identity not set")
        return
    try:
        profile = json.loads(out)
    except Exception:
        return
    login = profile.get("login") or ""
    uid = profile.get("id") or ""
    name = profile.get("name") or login
    email = "%s+%s@users.noreply.github.com" % (uid, login)
    if login:
        run(["git", "config", "--global", "user.name", name], timeout=30)
        run(["git", "config", "--global", "user.email", email], timeout=30)
        run(["git", "config", "--global", "init.defaultBranch", "main"], timeout=30)
        log("git identity set for %s" % login)


def step_uv():
    if version_of("uv") == PIN_UV:
        return True
    say("Installing uv %s (the tool that installs Python)." % PIN_UV)
    name = "uv-%s.tar.gz" % ARCH_UV
    base = "https://github.com/astral-sh/uv/releases/download/%s/" % PIN_UV
    archive = download(base + name, os.path.join(DL_DIR, name))
    if DRY_RUN:
        return True
    sidecar = fetch_text(base + name + ".sha256").split()[0].strip().lower()
    if hash_of(archive, "sha256").lower() != sidecar:
        raise StepError("The uv download did not match its official checksum.")
    work = os.path.join(DL_DIR, "uv-extract")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    extract_tar(archive, work)
    for tool in ("uv", "uvx"):
        binary = find_file(work, tool)
        if binary:
            install_file(binary, os.path.join(LOCAL_BIN, tool))
    if DRY_RUN:
        return True
    if version_of("uv") != PIN_UV:
        raise StepError("uv installed but does not report version %s." % PIN_UV)
    return True


def step_python():
    venv_version = venv_python_version() if path_is_owned(VENV_DIR) else None
    if version_of("python3") == PIN_PYTHON and venv_version == PIN_PYTHON:
        return True
    say("Installing Python %s." % PIN_PYTHON)
    if DRY_RUN:
        say("  (dry run) would install Python %s with uv" % PIN_PYTHON)
        return True
    code, _ = run(["uv", "python", "install", "--default", PIN_PYTHON], timeout=1800)
    if code != 0:
        raise StepError("Python %s could not be installed. Run me again." % PIN_PYTHON)
    if os.path.lexists(VENV_DIR):
        if not path_is_owned(VENV_DIR):
            raise StepError("An existing Python work folder has the wrong version and was left untouched: %s" % VENV_DIR)
        remove_owned_path(VENV_DIR)
    record_created_path(VENV_DIR)
    code, _ = run(["uv", "venv", "--seed", "--python", PIN_PYTHON, VENV_DIR], timeout=600)
    if code != 0:
        raise StepError("Python installed, but its work folder (venv) could not be made.")
    if version_of("python3") != PIN_PYTHON:
        raise StepError("Python installed but python3 does not report %s." % PIN_PYTHON)
    if venv_python_version() != PIN_PYTHON:
        raise StepError("The Python work folder does not contain Python %s." % PIN_PYTHON)
    return True


def step_node():
    node_home = os.path.join(OPT_DIR, "node-v%s" % PIN_NODE)
    if version_of("node") == PIN_NODE and os.path.isdir(node_home):
        return True
    if os.path.lexists(node_home) and not path_is_owned(node_home):
        raise StepError("An existing Node.js folder was not created by this setup and was left untouched: %s" % node_home)
    say("Installing Node.js %s." % PIN_NODE)
    name = "node-v%s-linux-%s.tar.xz" % (PIN_NODE, ARCH_NODE)
    url = "https://nodejs.org/dist/v%s/%s" % (PIN_NODE, name)
    archive = download(url, os.path.join(DL_DIR, name))
    if DRY_RUN:
        for tool in ("node", "npm", "npx", "corepack"):
            link_into_bin(os.path.join(node_home, "bin", tool))
        return True
    if MACHINE == "x86_64":
        if hash_of(archive, "sha256").lower() != PIN_NODE_SHA256_X64:
            raise StepError("The Node.js download did not match its official checksum.")
    else:
        sums = fetch_text("https://nodejs.org/dist/v%s/SHASUMS256.txt" % PIN_NODE)
        verify_from_sums(sums, name, archive, "sha256")
    if not DRY_RUN:
        if os.path.lexists(node_home):
            remove_owned_path(node_home)
        work = os.path.join(DL_DIR, "node-extract")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        extract_tar(archive, work)
        extracted = os.path.join(work, "node-v%s-linux-%s" % (PIN_NODE, ARCH_NODE))
        if not os.path.isdir(extracted):
            raise StepError("The Node.js download did not contain the expected program folder.")
        os.rename(extracted, node_home)
        record_created_path(node_home)
    for tool in ("node", "npm", "npx", "corepack"):
        link_into_bin(os.path.join(node_home, "bin", tool))
    if DRY_RUN:
        return True
    if version_of("node") != PIN_NODE:
        raise StepError("Node installed but does not report version %s." % PIN_NODE)
    return True


def step_bun():
    if version_of("bun") == PIN_BUN:
        return True
    say("Installing Bun %s." % PIN_BUN)
    name = "bun-linux-%s.zip" % ARCH_BUN
    base = "https://github.com/oven-sh/bun/releases/download/bun-v%s/" % PIN_BUN
    archive = download(base + name, os.path.join(DL_DIR, name))
    if DRY_RUN:
        return True
    try:
        sums = fetch_text(base + "SHASUMS256.txt")
        verify_from_sums(sums, name, archive, "sha256")
    except StepError:
        raise
    except Exception as err:  # noqa: BLE001
        raise StepError("Bun's checksum list could not be verified; the download was not installed.") from err
    work = os.path.join(DL_DIR, "bun-extract")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    if not DRY_RUN:
        extract_zip(archive, work)
    binary = find_file(work, "bun")
    if not binary and not DRY_RUN:
        raise StepError("The Bun download did not contain the bun program.")
    if binary:
        install_file(binary, os.path.join(LOCAL_BIN, "bun"))
    if DRY_RUN:
        return True
    if version_of("bun") != PIN_BUN:
        raise StepError("Bun installed but does not report version %s." % PIN_BUN)
    return True


def step_beads():
    if version_of("bd") == PIN_BD:
        return True
    say("Installing Beads (bd) %s." % PIN_BD)
    name = "beads_%s_linux_%s.tar.gz" % (PIN_BD, ARCH_GH)
    base = "https://github.com/gastownhall/beads/releases/download/v%s/" % PIN_BD
    archive = download(base + name, os.path.join(DL_DIR, name))
    if DRY_RUN:
        return True
    sums = fetch_text(base + "checksums.txt")
    verify_from_sums(sums, name, archive, "sha256")
    work = os.path.join(DL_DIR, "bd-extract")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    extract_tar(archive, work)
    binary = find_file(work, "bd")
    if not binary:
        raise StepError("The Beads download did not contain the bd program.")
    install_file(binary, os.path.join(LOCAL_BIN, "bd"))
    if DRY_RUN:
        return True
    if version_of("bd") != PIN_BD:
        raise StepError("Beads installed but does not report version %s." % PIN_BD)
    return True


def step_godot():
    godot_home = os.path.join(OPT_DIR, "godot-%s" % PIN_GODOT)
    binary_name = "Godot_v%s-stable_linux.%s" % (PIN_GODOT, ARCH_GODOT)
    if version_of("godot") and version_of("godot").startswith(PIN_GODOT):
        return True
    if os.path.lexists(godot_home) and not path_is_owned(godot_home):
        raise StepError("An existing Godot folder was not created by this setup and was left untouched: %s" % godot_home)
    say("Installing Godot %s (the copy the AI uses to test games)." % PIN_GODOT)
    name = binary_name + ".zip"
    base = "https://github.com/godotengine/godot/releases/download/%s-stable/" % PIN_GODOT
    archive = download(base + name, os.path.join(DL_DIR, name))
    if DRY_RUN:
        return True
    sums = fetch_text(base + "SHA512-SUMS.txt")
    verify_from_sums(sums, name, archive, "sha512")
    if not DRY_RUN:
        if os.path.lexists(godot_home):
            remove_owned_path(godot_home)
        os.makedirs(godot_home, exist_ok=True)
        record_created_path(godot_home)
        extract_zip(archive, godot_home)
        binary = os.path.join(godot_home, binary_name)
        if not os.path.exists(binary):
            found = find_file(godot_home, binary_name)
            if not found:
                raise StepError("The Godot download did not contain the Godot program.")
            binary = found
        os.chmod(binary, 0o755)
        link_into_bin(binary, "godot")
    if DRY_RUN:
        return True
    found_version = version_of("godot")
    if not found_version or not found_version.startswith(PIN_GODOT):
        raise StepError("Godot installed but does not report version %s." % PIN_GODOT)
    return True


def _ensure_opencode_config(state):
    """Create the user OpenCode config with the kit's default model, or
    add the model key to an existing config that has none. Never removes
    or changes anything else."""
    if os.path.exists(OPENCODE_CONFIG):
        try:
            with open(OPENCODE_CONFIG) as fh:
                config = json.load(fh)
        except Exception:
            say("Note: your OpenCode config exists but could not be read, so it was left alone.")
            return
        if "model" not in config:
            config["model"] = DEFAULT_MODEL
            if not DRY_RUN:
                with open(OPENCODE_CONFIG, "w") as fh:
                    json.dump(config, fh, indent=2)
            log("added default model to existing opencode config")
        return
    if not DRY_RUN:
        os.makedirs(os.path.dirname(OPENCODE_CONFIG), exist_ok=True)
        with open(OPENCODE_CONFIG, "w") as fh:
            json.dump({"$schema": "https://opencode.ai/config.json",
                       "model": DEFAULT_MODEL}, fh, indent=2)
        state.setdefault("created", {})["opencode_config"] = True
        save_state(state)
    log("created opencode config with default model %s" % DEFAULT_MODEL)


def step_opencode(state, skip_auth):
    if version_of("opencode") != PIN_OPENCODE:
        opencode_path = os.path.join(LOCAL_BIN, "opencode")
        if os.path.lexists(opencode_path) and not path_is_owned(opencode_path):
            raise StepError("An existing OpenCode entry was not created by this setup and was left untouched: %s" % opencode_path)
        say("Installing OpenCode %s." % PIN_OPENCODE)
        code, _ = run(["npm", "install", "-g", "--prefix", os.path.join(HOME, ".local"),
                       "@opencode/cli@%s" % PIN_OPENCODE], timeout=1800)
        if DRY_RUN:
            return True
        if code != 0:
            raise StepError("OpenCode could not be installed. Run me again.")
        if version_of("opencode") != PIN_OPENCODE:
            raise StepError("OpenCode installed but does not report version %s." % PIN_OPENCODE)
        if os.path.lexists(opencode_path):
            record_created_path(opencode_path)
    _ensure_opencode_config(state)
    code, out = run(["opencode", "auth", "list"], timeout=60)
    authed = code == 0 and bool(out.strip()) and "0 credentials" not in out
    if authed:
        return True
    if skip_auth:
        say("Skipping the OpenCode sign-in (testing mode).")
        return True
    say("")
    say("STEP: Sign in to OpenCode.")
    say("This is the account the AI runs on. A list will appear: choose OpenCode Zen.")
    say("The browser will open so you can make your account or sign in.")
    say("The AI model this kit uses (Big Pickle) is free, so signing up should")
    say("not ask for a payment method. If any screen asks you to pay, stop")
    say("and open an issue at %s." % ISSUES_URL)
    say("Press Enter when you are ready.")
    if not DRY_RUN:
        input()
    code, _ = run(["opencode", "auth", "login"], inherit=True, timeout=1800)
    if code != 0:
        say("Note: the OpenCode sign-in did not finish. You can do it later by typing: opencode auth login")
    return True


STARTER_PROJECT = """; Engine configuration file.
; It's best edited using the editor UI and not directly.

config_version=5

[application]

config/name="My First Game"
config/features=PackedStringArray("4.7", "GL Compatibility")

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

STARTER_README = """# My First Game

A starter Godot project, created by the godot-baseline setup.

To work on it: open OpenCode in this folder.
To play it: open this project in Godot on Windows and press Play.
"""


def step_starter():
    project_file = os.path.join(STARTER_DIR, "project.godot")
    if os.path.exists(project_file):
        return True
    say("Creating the starter Godot project.")
    if DRY_RUN:
        return True
    os.makedirs(STARTER_DIR, exist_ok=True)
    with open(project_file, "w") as fh:
        fh.write(STARTER_PROJECT)
    with open(os.path.join(STARTER_DIR, "README.md"), "w") as fh:
        fh.write(STARTER_README)
    log("starter project created at %s" % STARTER_DIR)
    return True


def _soft(cmd, timeout=300):
    try:
        code, out = run(cmd, timeout=timeout)
        return code, out
    except Exception as err:  # noqa: BLE001
        return 1, str(err)


def doctor(write_report=True):
    """Returns (hard_failures, lines). Each line is (mark, text)."""
    lines = []
    hard = 0

    def check(ok, label, detail="", warn_only=False):
        nonlocal hard
        if ok:
            lines.append(("PASS", label + (" (%s)" % detail if detail else "")))
        elif warn_only:
            lines.append(("WARN", label + (" (%s)" % detail if detail else "")))
        else:
            hard += 1
            lines.append(("FAIL", label + (" (%s)" % detail if detail else "")))

    check(have("git"), "git is installed", version_of("git") or "")
    check(have("jq"), "jq is installed")
    check(have("curl"), "curl is installed")
    check(have("rg"), "ripgrep is installed", warn_only=True)
    check(have("unzip"), "unzip is installed", warn_only=True)
    check(version_of("gh") == PIN_GH, "GitHub tool (gh)", version_of("gh") or "missing")
    code, _ = sh("gh auth status", timeout=60)
    check(code == 0, "Signed in to GitHub", warn_only=True)
    check(version_of("uv") == PIN_UV, "uv", version_of("uv") or "missing")
    check(version_of("python3") == PIN_PYTHON, "Python", version_of("python3") or "missing")
    check(os.path.isdir(VENV_DIR), "Python work folder (venv)", warn_only=True)
    check(version_of("node") == PIN_NODE, "Node.js", version_of("node") or "missing")
    check(version_of("bun") == PIN_BUN, "Bun", version_of("bun") or "missing", warn_only=True)
    check(version_of("bd") == PIN_BD, "Beads (bd)", version_of("bd") or "missing")
    gv = version_of("godot")
    check(bool(gv and gv.startswith(PIN_GODOT)), "Godot for the AI", gv or "missing")
    check(version_of("opencode") == PIN_OPENCODE, "OpenCode", version_of("opencode") or "missing")
    model_ok = False
    try:
        with open(OPENCODE_CONFIG) as fh:
            model_ok = json.load(fh).get("model") == DEFAULT_MODEL
    except Exception:
        model_ok = False
    check(model_ok, "OpenCode default model is set", DEFAULT_MODEL, warn_only=True)
    code, out = _soft(["opencode", "auth", "list"], timeout=60)
    check(code == 0 and bool(out.strip()) and "0 credentials" not in out,
          "Signed in to OpenCode", warn_only=True)
    starter = os.path.join(STARTER_DIR, "project.godot")
    check(os.path.exists(starter), "Starter project exists", warn_only=True)
    if write_report and not DRY_RUN:
        with open(REPORT_FILE, "w") as fh:
            fh.write("godot-baseline report\n")
            fh.write("When: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
            fh.write("Machine: %s %s\n" % (platform.system(), MACHINE))
            code, out = sh("lsb_release -d 2>/dev/null || cat /etc/os-release | head -1", timeout=30)
            fh.write("System: %s\n\n" % out.strip())
            for mark, text in lines:
                fh.write("[%s] %s\n" % (mark, text))
            fh.write("\nLog file: %s\n" % LOG_FILE)
    return hard, lines


def print_lines(lines):
    for mark, text in lines:
        symbol = {"PASS": "[ OK ]", "WARN": "[warn]", "FAIL": "[FAIL]"}[mark]
        say("%s %s" % (symbol, text))


def do_install(args, repair=False):
    state = load_state()
    steps = [
        ("apt", "Basic tools", lambda: step_apt()),
        ("gh", "GitHub tool", lambda: step_gh()),
        ("gh_auth", "GitHub sign-in", lambda: step_gh_auth(args.skip_auth)),
        ("uv", "uv", lambda: step_uv()),
        ("python", "Python", lambda: step_python()),
        ("node", "Node.js", lambda: step_node()),
        ("bun", "Bun", lambda: step_bun()),
        ("beads", "Beads", lambda: step_beads()),
        ("godot", "Godot", lambda: step_godot()),
        ("opencode", "OpenCode", lambda: step_opencode(state, args.skip_auth)),
    ]
    if not args.skip_starter:
        steps.append(("starter", "Starter project", lambda: step_starter()))
    if args.skip_apt:
        steps = [s for s in steps if s[0] != "apt"]
    ensure_path_block()
    for key, label, fn in steps:
        done_at_pin = state.get("steps", {}).get(key) == "ok" and not repair
        say("")
        say("--- %s ---" % label)
        try:
            fn()
        except StepError as err:
            say("")
            say("STOPPED at: %s" % label)
            say(str(err))
            say("The setup stopped before finishing. Run the setup command again to resume.")
            say("If it stops again, the details are in the log: %s" % LOG_FILE)
            return 1
        state.setdefault("steps", {})[key] = "ok"
        save_state(state)
        log("step ok: %s (previously recorded: %s)" % (key, done_at_pin))
    if DRY_RUN:
        say("")
        say("Dry run complete. No setup files were created or changed.")
        return 0
    say("")
    say("--- Checking everything ---")
    hard, lines = doctor()
    print_lines(lines)
    if hard:
        say("")
        say("%d thing(s) still need attention. The report is at: %s" % (hard, REPORT_FILE))
        say("Include it if you ask for help: %s" % ISSUES_URL)
        return 1
    say("")
    say("All done. Everything is installed and checked.")
    say("Next: open Ubuntu, go to ~/my-first-game, and start OpenCode.")
    say("The guide (GUIDE.md) shows you how, in Part 5.")
    return 0


def do_uninstall():
    state = load_state()
    removed = []
    for path in reversed(state.get("created", {}).get("paths", [])):
        path = os.path.abspath(path)
        allowed = (path == VENV_DIR or path.startswith(LOCAL_BIN + os.sep)
                   or path.startswith(OPT_DIR + os.sep))
        if allowed and os.path.lexists(path):
            remove_owned_path(path)
            removed.append(path)
    if state.get("created", {}).get("opencode_config") and os.path.exists(OPENCODE_CONFIG):
        os.remove(OPENCODE_CONFIG)
        removed.append(OPENCODE_CONFIG)
    for rc_name in (".bashrc", ".profile"):
        rc_path = os.path.join(HOME, rc_name)
        try:
            with open(rc_path) as fh:
                content = fh.read()
            content = content.replace(
                '\n# >>> godot-baseline >>>\nexport PATH="$HOME/.local/bin:$PATH"\n# <<< godot-baseline <<<\n', "")
            with open(rc_path, "w") as fh:
                fh.write(content)
        except Exception:
            pass
    say("Removed: %s" % (", ".join(removed) if removed else "nothing tracked as installed"))
    say("Kept setup state and logs at: %s" % STATE_DIR)
    say("Left in place on purpose: your projects and files (including %s)" % STARTER_DIR)
    return 0


def main(argv=None):
    global DRY_RUN, LOG_FH
    parser = argparse.ArgumentParser(description="godot-baseline setup script (runs inside WSL)")
    parser.add_argument("verb", choices=["install", "doctor", "repair", "uninstall"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-apt", action="store_true")
    parser.add_argument("--skip-auth", action="store_true")
    parser.add_argument("--skip-starter", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run and args.verb not in ("install", "repair"):
        parser.error("--dry-run can only be used with install or repair")
    DRY_RUN = args.dry_run
    if not DRY_RUN and args.verb in ("install", "repair", "doctor"):
        os.makedirs(STATE_DIR, exist_ok=True)
        LOG_FH = open(LOG_FILE, "a")
    log("setup.py %s (dry_run=%s)" % (args.verb, DRY_RUN))
    say("godot-baseline setup (inside Ubuntu)")
    if args.verb == "doctor":
        hard, lines = doctor()
        print_lines(lines)
        say("")
        say("Report written to: %s" % REPORT_FILE)
        return 1 if hard else 0
    if args.verb == "uninstall":
        return do_uninstall()
    return do_install(args, repair=(args.verb == "repair"))


if __name__ == "__main__":
    sys.exit(main())
