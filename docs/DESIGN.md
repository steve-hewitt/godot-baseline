# Design

The kit's technical design: what it installs, in what order, at which versions, and why. It describes the current build, not the history of how the build was decided.

## Purpose

Take a clean Windows 11 machine to a working Godot development baseline: WSL2 Ubuntu, a pinned toolchain, OpenCode, and a starter Godot project. Team features and extra tooling can be added on top later.

## Inventory

### Windows side (installed by the guide's typed commands, via winget)

- WSL2 with Ubuntu 26.04 LTS (preferred; the guide falls back to the plain `Ubuntu` name if 26.04 is not offered)
- Windows Terminal (already on Windows 11)
- VS Code, plus the WSL Remote extension
- Godot 4.7.2, standard build, for the human to open, look at, and play games

### WSL side (installed by the setup script, in this order)

1. Ubuntu updates
2. git
3. jq, curl, ripgrep, unzip
4. GitHub CLI (`gh`), with a browser sign-in early in the run; git identity is configured from the account
5. uv, and Python 3.15.2 installed by uv (Ubuntu's apt Python cannot reach the pin, and a source build would require build-essential)
6. Node.js LTS, and Bun
7. Godot 4.7.2 for Linux, headless, the copy the AI uses to import and test games
8. OpenCode 2.3.0, with the user's own account login
9. A starter game project at `~/my-first-game`

### Accounts (the user's own, created during setup)

- GitHub account, used to set the git name and email
- OpenCode account (Zen or Go), for model access. OpenCode with no login is an empty shell.

## Design decisions

- **One setup script plus typed Windows commands.** There is no Windows-side script. The Windows jobs (winget apps, WSL and Ubuntu install, the reboot in the middle) are typed commands in GUIDE.md, one command per job, all from Microsoft's catalog. The Python setup script inside WSL does everything else, started by one typed line through `wsl.exe` that fetches it from this repository at a pinned tag.
- **Minimal manual steps.** The human's job is the 10 steps in GUIDE.md. Creating the Ubuntu username and password is the one step no script can do. The account sign-ins are the other human-only steps, because the credentials belong to the user.
- **Git, gh, VS Code, and Node/Bun are part of the baseline.** No git means no version control; gh provides the GitHub sign-in flow and the git identity; Node and Bun are the runtimes OpenCode uses.
- **jq and curl are hard requirements.** curl is what every installer download runs on. jq is kept as part of the base toolchain for future tooling that reads JSON.
- **ripgrep and unzip are included** as cheap insurance in the same apt step. They cost seconds and a few MB, and remove a class of command-not-found detours when models or asset packs reach for them.
- **build-essential is out of the base kit.** Nothing in the stack compiles native code, and it is hundreds of MB. It can be added later if a component needs compilation.
- **Godot topology:** Linux headless Godot inside WSL for OpenCode, Windows Godot GUI for the human. Agent-worked projects live on the WSL side; the human plays them in Windows Godot over the `\\wsl$` path, which is a known limitation.
- **No Windows safety setting is changed.** There is no PowerShell script in the kit, so no execution-policy question arises. The Windows side installs only Microsoft-catalog apps.
- **Public install source.** The repository is public and the guide fetches the setup script from a pinned release tag. No credentials are needed for the fetch, and nothing script-shaped lands on the Windows side.

## Version pins

Pinned to the current latest of each component, checked upstream on 2026-11-16.

| Component | Pin | Evidence |
| --- | --- | --- |
| OpenCode | 2.3.0 | GitHub release v2.3.0, published 2026-11-13; npm `@opencode/cli` latest is 2.3.0. Caution: GitHub's "latest release" endpoint points at the 1.x line (v1.19.5), which is not the newest version; the 2.x line is what this kit installs. |
| Python | 3.15.2 | Latest release of the 3.15 line (endoflife.date, checked 2026-11-16). Ubuntu apt cannot supply it (24.04 ships 3.12, 26.04 ships 3.14), and a source build would need build-essential, which is out. The setup script therefore installs uv and lets uv install Python. |
| Godot | 4.7.2 | Latest stable (4.7.2-stable, 2026-08-18). Do not chase future Godot releases casually: opening a project in a newer Godot can upgrade its files one-way. |
| Node.js | v26.13.1 LTS (Lithium) | nodejs.org dist index, checked 2026-11-16. Soft pin: Node is a tooling runtime here, and nothing is validated against a specific Node version. |
| GitHub CLI (`gh`) | 2.104.0 | Latest GitHub release (cli/cli), checked 2026-11-16. |
| uv | 0.13.8 | Latest GitHub release (astral-sh/uv), checked 2026-11-16. |
| Bun | 1.4.4 | Latest GitHub release (oven-sh/bun), checked 2026-11-16. |

## Default model

`opencode/big-pickle`, free on OpenCode Zen. Verified against the live roster on 2026-11-16: $0 in/out, 200K context, 32K output, tool calls supported. The setup script sets it in the OpenCode config (creating the config if absent; adding only the model key if a config already exists).

Free Zen lanes are promotional and can change or disappear. If this one disappears, `DEFAULT_MODEL` in `scripts/wsl/setup.py` is the one line to change.

## Known limitations

- The play path is Windows Godot opening a WSL-side project over `\\wsl$`: workable, slow, and the guide says so.
- The Windows-side typed commands have not been tested on a clean Windows machine.
- If the computer's firmware has virtualization disabled, WSL cannot install, and the guide has no branch for it.
- Free Zen model lanes are promotional and can vanish.
- Godot .NET is not included. It is only relevant if the project adopts C#.

## Out of scope

- Teaching game development fundamentals
- Ollama, Headroom, and local models
- ComfyUI and media generation
- Bundled agents and commands; these can layer on top later
