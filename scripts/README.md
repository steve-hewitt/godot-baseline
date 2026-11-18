# Scripts

One script. The Windows side has no script; it uses typed commands in GUIDE.md. See `docs/DESIGN.md` for the design.

## The Windows side: typed commands in the guide, no script

GUIDE.md Part 1 has the user type these commands in an admin Terminal, one job each, all from Microsoft's own catalog:

```
winget install --id Microsoft.VisualStudioCode --exact --accept-package-agreements --accept-source-agreements
code --install-extension ms-vscode-remote.remote-wsl
winget install --id GodotEngine.GodotEngine --exact --version 4.7.2 --accept-package-agreements --accept-source-agreements
wsl --install -d Ubuntu-26.04
```

After the restart and the Ubuntu account step, GUIDE.md Part 3 starts the setup script from the Terminal: a `python3 --version` check inside the distro (with a root apt command that adds Python if the check fails), then one command that fetches the script into Ubuntu and runs it:

```
wsl -- bash -lc 'curl -fsSL https://raw.githubusercontent.com/steve-hewitt/godot-baseline/v0.1.0/scripts/wsl/setup.py -o ~/setup.py && python3 ~/setup.py install'
```

## `wsl/setup.py`

The setup script. Runs inside Ubuntu on the stock Python 3, standard library only. Verbs:

```
python3 setup.py install     # install, or finish an earlier run
python3 setup.py doctor      # check installed tools, write the report file
python3 setup.py repair      # re-check every step, redo anything wrong
python3 setup.py uninstall   # remove tracked kit files (projects stay)
```

Choose a verb explicitly; running the script without one does not start an install. `--dry-run` is available for `install` and `repair` and does not create setup files. `--skip-apt`, `--skip-auth`, and `--skip-starter` exist for testing.

Install order, each step check-before-act with version verification against the pins in `docs/DESIGN.md`:

1. apt: git, jq, curl, ripgrep, unzip, ca-certificates (one sudo password prompt, refreshed as needed)
2. GitHub CLI 2.104.0 (release tarball, sha256 verified against the release checksums)
3. GitHub sign-in pause (early, so git identity is configured before the rest), then `gh auth setup-git` and git identity from the GitHub profile (name, and the account's noreply email)
4. uv 0.13.8 (tarball, sha256 sidecar verified), then Python 3.15.2 via `uv python install --default`, plus a seeded venv at `~/.venvs/baseline`
5. Node.js 26.13.1 (tarball, sha256 verified; symlinks into `~/.local/bin`)
6. Bun 1.4.4 (zip, sha256 verified against the release sums)
7. Godot 4.7.2 Linux (zip, sha512 verified; linked as `godot`)
8. OpenCode 2.3.0 (`npm install -g @opencode/cli`), user config created only if absent (default model added to an existing config only if it has none), then the OpenCode sign-in pause, which states that the kit model is free
9. Starter Godot project created at `~/my-first-game`

Then a doctor pass runs automatically. Doctor prints the tick list, and writes `~/godot-baseline-report.txt` (versions, check results, log location): the file to include if you ask for help. The doctor checks the starter project exists but does not run Godot's project import.

Guarantees: every download is checksum-verified against its upstream sums file; checksum failures stop the install; pre-existing files in tool destinations are left untouched; uninstall removes only paths recorded as created by this setup and leaves shared directories and setup logs in place; no existing user config is overwritten; a failure stops the run with a plain-language message and a resume path, never a half-hidden state; everything the script does is logged to `~/.local/state/godot-baseline/setup.log`.
