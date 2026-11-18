# Godot Baseline

A setup kit that takes a clean Windows 11 machine to a working Godot development baseline: VS Code, Godot, WSL2 Ubuntu, and a pinned toolchain for AI-assisted Godot projects.

Setup is a short series of typed commands on Windows and one script inside Ubuntu. No Windows safety setting is changed, and every downloaded file is checked against its maker's published checksum.

## Status

At v0.1.0. The Ubuntu setup script has been rehearsed end to end on Ubuntu 24.04 in a throwaway home directory: every pinned tool installed at its exact version, the self-check passed, and an interrupted run resumed correctly. The Windows-side typed commands have not yet been run on a clean Windows machine.

## What it installs

**Windows side**, by typed commands from Microsoft's catalog:

- VS Code, with its WSL extension
- Godot 4.7.2
- WSL2 with Ubuntu 26.04 LTS (the guide falls back to the plain `Ubuntu` name if 26.04 is not offered)

**Ubuntu side**, by one setup script:

- git, jq, curl, ripgrep, unzip
- GitHub CLI
- uv and Python 3.15.2
- Node.js and Bun
- Godot 4.7.2, headless
- OpenCode
- A starter Godot project at `~/my-first-game`

## How it works

1. Type the Windows install commands in Windows Terminal as an administrator: VS Code, its WSL extension, Godot, and Ubuntu.
2. Restart if Windows asks, then create the Ubuntu username and password.
3. Type one command inside Ubuntu. It downloads `scripts/wsl/setup.py` from this repository at tag `v0.1.0` and runs it. The script checks each step before acting, verifies every pinned version, and checksum-verifies every download.
4. Sign in to GitHub (which sets your git name and email) and OpenCode (which provides the AI model) when the script pauses.

The human steps are in [GUIDE.md](GUIDE.md). The finish line is giving OpenCode a one-sentence game idea and letting it take a first swing at building and testing it.

## Docs

- [GUIDE.md](GUIDE.md): the step-by-step setup guide.
- [docs/DESIGN.md](docs/DESIGN.md): the inventory, install order, version pins, and design rationale.
- [scripts/README.md](scripts/README.md): the setup script and its verbs.

## Principles

- Check before acting: the Ubuntu setup script checks what is already done and can resume after an interruption. Follow the guide's instructions before repeating Windows commands.
- Pin every version in one place. Nothing installs at "latest".
- No safety setting is ever changed or overridden, and there is no Windows-side script. The Windows side is typed commands that install Microsoft-catalog apps only. The one script runs inside Ubuntu and checksum-verifies every file it downloads.
- Baseline only: no local models, no media tools, no bundled agents.

## Help

Open an issue at <https://github.com/steve-hewitt/godot-baseline/issues>. If the setup script wrote `~/godot-baseline-report.txt`, include it.
