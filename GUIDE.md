# Set Up Your Computer for Godot Game Development

A step-by-step guide. Follow it from the top. Do not skip steps.

**How this works:** you type a few short commands on the Windows side, then one script does the rest of the work inside Ubuntu.

**How long it takes:** about an hour, and most of that is waiting for downloads. This is an estimate, not a promise. A slow internet connection makes it longer.

**What it costs:** the software and AI model listed here are free to use as of November 2026. You will need internet access and GitHub and OpenCode accounts. Provider plans can change; if a screen asks you to pay, stop and check the help section at the end.

**If setup is interrupted:** return to the step you were on. The Ubuntu setup script checks what is already installed and can resume; follow each step's instructions before repeating a Windows command.

## Before you start

You need:

- A computer with Windows 11, and the right to install things on it (an administrator account).
- The computer plugged into power.
- An internet connection.
- An email address you can open on this computer.
- A method of your choice to write down two passwords.

Words used in this guide:

- **Windows side:** your normal computer, the desktop and Start menu you already know.
- **Windows Terminal:** the Windows app where you type or paste commands and press Enter.
- **Ubuntu window:** a second system that lives inside Windows. The game tools run there, in a window with text.
- **Script:** a file that does a list of jobs for you, so you do not have to enter each command.
- **Pinned version:** the exact version this setup installs, rather than whichever version is newest.
- **Checksum:** a file's digital fingerprint, used to check that a download matches the publisher's original.
- **Headless:** running without opening a window to show the game.

## Part 1: The Windows side, typed by hand

Four short commands, typed one at a time. Each one installs one thing, and the window tells you when it is done.

**Step 1. Open Windows Terminal as administrator.**

1. Click the **Start** button.
2. Type the word **Terminal**.
3. Right-click **Windows Terminal** in the list.
4. Click **Run as administrator**.
5. A box asks if you want to allow changes. Click **Yes**.
6. A dark window opens. This is Windows Terminal. Leave it open.

**Step 2. Install VS Code, and its Ubuntu add-on.**

VS Code is the program for looking at code and project files.

1. Click in the Windows Terminal window.
2. Paste this command, exactly, and press **Enter**.

   `winget install --id Microsoft.VisualStudioCode --exact --accept-package-agreements --accept-source-agreements`

3. Wait until the window says it finished. This can take a few minutes.
4. Paste this command and press **Enter**. It adds the part of VS Code that can look inside Ubuntu.

   `code --install-extension ms-vscode-remote.remote-wsl`

5. If the window says "code" is not recognized, that is a known hiccup with a just-installed app: close Windows Terminal, do Step 1 again, and run only the second command.

**Step 3. Install Godot, and check its version.**

Godot is the program you open yourself to see and play games.

1. Paste this command and press **Enter**.

   `winget install --id GodotEngine.GodotEngine --exact --version 4.7.2 --accept-package-agreements --accept-source-agreements`

2. Wait until it finishes.
3. Open **Godot** from the Start menu. Its first screen shows its version number. It should say **4.7.2**. Close Godot again.
4. If the version says anything else, or Godot is not there, do not try to fix it. Make a note of what you see and carry on. The rest of the setup still works, and you can report this at the end.

**Step 4. Install Ubuntu.**

1. Paste this command and press **Enter**.

   `wsl --install -d Ubuntu-26.04`

2. If the window says that name was not found, paste this command instead, and make a note that you used the second one.

   `wsl --install -d Ubuntu`

3. Wait. This downloads Ubuntu, and it can take a while.

**Step 5. Restart if the computer asks.**

1. If Windows says it needs to restart, let it restart.
2. Sign back in to Windows. Nothing starts by itself after the restart. That is fine. Go on to Part 2.

## Part 2: Make your Ubuntu account

No script can do this part. Ubuntu needs a username and password that belong to you.

**Step 6. Create your username and password.**

1. Click **Start**, type **Ubuntu**, and open it.
2. It asks for a username. Type a short name: lowercase letters, one word, no spaces. Press **Enter**.
3. It asks for a password. Type one and press **Enter**.
4. It asks again. Type the same password and press **Enter**.
5. Important: while you type the password, the screen shows nothing at all. No dots, no stars. That is normal. Keep typing.
6. Write the username and password on your paper. You will need this password again in Part 3.

## Part 3: Start the main setup

**Step 7. Start the setup script inside Ubuntu.**

The rest of the setup is one script, and it runs inside Ubuntu. You start it from Windows Terminal with a few short commands.

1. Click the Windows Terminal window from Part 1. If you closed it, open **Windows Terminal** again from the Start menu.
2. Paste this command and press **Enter**. It checks that Ubuntu has Python, which the script needs.

   `wsl -- python3 --version`

3. If a line starting with **Python 3** appears, go to point 5.
4. If you see an error instead, paste this command and press **Enter**. It adds Python to Ubuntu. When it finishes, run the command from point 2 once more to check.

   `wsl -u root -- bash -lc 'apt-get update && apt-get install -y python3 ca-certificates'`

5. Paste this command and press **Enter**. It downloads the setup script from this repository into Ubuntu, and starts it.

   `wsl -- bash -lc 'curl -fsSL https://raw.githubusercontent.com/steve-hewitt/godot-baseline/v0.1.0/scripts/wsl/setup.py -o ~/setup.py && python3 ~/setup.py install'`

6. Stay with this window. The script works through the list below. It asks for your Ubuntu password near the start, and it pauses twice for sign-ins in Part 4.

**What the script installs**, inside Ubuntu, in this order. It checks each one before moving on, and skips any that are already there.

1. **Updates** for Ubuntu itself.
2. **Git**, the tool that keeps copies of projects and tracks every change.
3. **Small helper tools:** jq, curl, ripgrep, and unzip. The setup script needs curl, and the other tools are there so nothing the AI tries to use is missing.
4. **GitHub CLI**, the tool that signs you in to GitHub (Part 4).
5. **Python 3**, with the parts it needs to run the AI tools.
6. **Node.js and Bun**, which OpenCode and its add-ons run on.
7. **Godot for Linux**, a version with no screen of its own. The AI uses this one to test games by itself.
8. **OpenCode**, the program where you talk to the AI and it builds games.
9. **A starter game project**, called `my-first-game`, ready for your first try.

Every file the script downloads is checked against its maker's published checksum before it is used.

Three things were installed on the Windows side in Part 1, by your own typed commands:

- **Ubuntu** itself, living inside Windows.
- **VS Code**, with an add-on that lets it look inside Ubuntu.
- **Godot for Windows**, the version you open yourself to see and play games.

## Part 4: Two sign-ins

The script pauses twice. Both times, your web browser opens. This is the part only you can do, because these are your accounts.

**Step 8. Sign in to GitHub.**

Signing in to GitHub also sets the name and email that git uses on this machine.

1. If you do not have a GitHub account, make one now, in the browser window that opened. Use your email address and pick a username.
2. The script shows you a short code. Type that code into the browser page.
3. Click the button to approve.
4. Go back to the Windows Terminal window. The script carries on by itself.

**Step 9. Sign in to OpenCode.**

1. The browser opens again, on the OpenCode sign-in page. In the list, choose **OpenCode Zen**.
2. Make your account, or sign in if you already have one.
3. The model this kit uses is currently listed as free, but provider plans can change. If a screen asks you to pay, stop and check the help section at the end of this guide.
4. Click the button to approve.
5. Go back to the Windows Terminal window. The script carries on by itself.

## Part 5: Checks, and your first game

**Step 10. Wait for the setup checks.**

1. At the end, the script checks everything, one line at a time: **[ OK ]** means it passed, **[warn]** means it needs attention but did not stop setup, and **[FAIL]** means a required check failed.
2. If there are no **[FAIL]** lines, setup is complete. You can ask for help with any warnings using the report.
3. If you see **[FAIL]**, do not guess at a fix. The script writes a report to `~/godot-baseline-report.txt`. Use the help section at the end to open an issue and include the report.

**Make your first game.**

1. Open **Ubuntu** from the Start menu. (Not Windows Terminal from Part 1. That is on the Windows side; your game is on the Ubuntu side.)
2. In the Ubuntu window, type `cd my-first-game` and press Enter.
3. Type `opencode` and press Enter.
4. OpenCode opens. Type one sentence that says what game you want. For example: "Make a simple game where a knight collects coins in a castle and avoids slimes."
5. Press Enter and let OpenCode take a first swing at planning, building, and testing the game with Linux Godot. This takes a while.
6. To play your game: open **Godot** on the Windows side. In the open-project box, type `\\wsl$` and press Enter, then browse to your Ubuntu name, then `my-first-game`, and open it. Press the **Play** button (the triangle at the top). Opening it this way can be slow. That is a known limitation, not something you did wrong.

**See the finished example.** OpenCode built *Knight's Hoard* from the sentence above. Play it in your browser at <https://steve-hewitt.github.io/godot-baseline/>.

## If something goes wrong

- **"I type my password and nothing appears."** That is how Ubuntu works. Type it anyway and press Enter.
- **"The computer restarted in the middle."** Sign in and return to the step you were on. If setup had started, open Windows Terminal and run the setup command from Step 7 again to resume. For other commands, follow the instructions in that step before repeating them.
- **"A command says the app is already installed."** It may already be there. Follow the next check or instruction in that step before moving on.
- **"A command says 'code' is not recognized."** Close Windows Terminal, open it again as in Step 1, and run the command once more.
- **"I closed the Ubuntu window."** Nothing is lost. Open Ubuntu again from the Start menu.
- **"There is a lot of red text."** Some installers show warnings in red. If setup is still running, wait for the final checks. If it stops, follow the message on screen.
- **"Setup stopped and I do not know why."** Note the last message. Run the setup command from Step 7 again to resume; if it stops again, copy the last few lines or take a screenshot, then ask for help using the details below. Include the report if one was written.

## What you end up with

- Windows side: VS Code, Godot (for playing and looking at games), Ubuntu running inside Windows.
- Ubuntu side: Git, Python 3, Node.js, OpenCode, Godot (for the AI to test games), and a starter project at `~/my-first-game`.
- Accounts: GitHub (which sets your git identity) and OpenCode (the AI), both yours.

## If you need help

Open an issue at <https://github.com/steve-hewitt/godot-baseline/issues>. Include the step you were on, what you saw, and `~/godot-baseline-report.txt` if the setup script wrote one.
