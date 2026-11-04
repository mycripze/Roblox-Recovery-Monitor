# Roblox Recovery Monitor

This Windows 11 helper monitors the official Roblox Player process. When Roblox
closes, it opens the selected Player shortcut, waits for Roblox to appear, waits
the configured delay, and replays your saved mouse path, clicks, and vertical
scrolls.

## Run

Python 3.10 or later is required. The app uses only the Python standard library.

For the packaged Windows app, run
`dist\Roblox Recovery Monitor.exe`; Python is not needed to run that build.

Double-click `Run Roblox Recovery Monitor.bat`, or run:

```powershell
python .\roblox_recovery.py
```

Use **Browse** beside the Roblox Player shortcut field to select its `.lnk` or
`.exe` file if it is not found automatically.

## Record actions

1. Open Roblox to the screen where you want the sequence to start.
2. Press the displayed recorder shortcut (default **Ctrl+Shift+R**) or click
   **Record actions**.
3. Switch to Roblox, move the pointer along the path you want replayed, and
   perform the desired scrolls and clicks.
4. Press the recorder shortcut again to stop and save the recording.
5. Click **Start monitoring**.

To change the recorder shortcut, click its box and press a combination
containing Ctrl, Shift, or Alt and a supported key. Mouse movement, clicks, and
vertical scrolls are recorded only while Roblox is the foreground app. Keyboard
input is not recorded. Positions are relative to the Roblox window, so they
adapt to its size. The sequence is positional and does not verify which
experience is selected. The recording is saved locally in
`%LOCALAPPDATA%\RobloxRecoveryMonitor\actions.json`.

The pointer follows the recorded path and timing instead of jumping to each
click. Use the **Mouse glide speed** slider to scale delays: `1.00x` is recorded
pace, values above it are faster, and values below it are slower. The range is
`0.25x` to `10.00x`.

## Monitoring settings and history

The open timeout controls how long the monitor waits for Roblox to appear after
launching it (default 60 seconds; allowed range 1–3600 seconds). The
post-open wait controls how long Roblox must remain open before replay begins
(default 5 seconds; allowed range 0–600 seconds). Settings are saved locally.

If Roblox is already open when monitoring starts, the app waits for it to close
before reopening it. If Roblox is closed when monitoring starts, it waits until
it opens and then monitors for a later closure. Click **Stop monitoring** before
intentionally closing Roblox.

The live elapsed-time stopwatch starts with each monitoring run. When monitoring
stops, the app records a separate session containing the date, start time, end
time, and elapsed time. Session data is saved locally in
`%LOCALAPPDATA%\RobloxRecoveryMonitor\monitoring_sessions.json` and displayed
above the relaunch history.

History entries show the full reason text and wrap to fit the resized window.
Use **Browse** or edit **Save location** to choose the history JSON file. Use
**Clear history** to remove entries from all time, the last hour, 24 hours, 7
days, or 30 days.

A successful entry means Roblox was detected, remained open through the
configured wait, and the saved mouse path, clicks, and scrolls were sent. It
does not confirm that the game actually opened.

## Build the executable

Install PyInstaller, then build a one-file, windowed executable from the project
folder:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "Roblox Recovery Monitor" .\roblox_recovery.py
```

The executable is written to `dist\Roblox Recovery Monitor.exe`. To set a
custom Windows executable icon, add `--icon ".\your-icon.ico"` to the build
command. The generated `build` folder is temporary and is not included in the
source repository.

## Project files

- `roblox_recovery.py` — application source.
- `Roblox Recovery Monitor.bat` — launches the Python source version.
- `Roblox Recovery Monitor.spec` — PyInstaller build configuration.
- `dist\Roblox Recovery Monitor.exe` — packaged Windows executable.
- `README.md` — setup, use, settings, and build instructions.
