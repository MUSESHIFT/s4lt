# S4LT - Sims 4 Linux Toolkit

**Native mod manager for Linux and Steam Deck. No Wine. No Proton. Just works.**

---

## Download

**[S4LT-0.7.0-x86_64.AppImage](https://github.com/yourname/s4lt/releases/download/v0.7.0/S4LT-0.7.0-x86_64.AppImage)** (27 MB)

---

## Installation (3 Steps)

### Linux Desktop

1. **Download** the AppImage file
2. **Right-click** the file → Properties → Permissions → Check "Allow executing as program"
3. **Double-click** to run

That's it! A native window will open with the S4LT interface.

### Steam Deck

1. **Switch to Desktop Mode** (hold Power button → Desktop Mode)
2. **Download** the AppImage to your Desktop
3. **Right-click** the file → Properties → Permissions → Check "Is Executable"
4. **Double-click** to launch

**Tip:** To use in Gaming Mode, add S4LT as a non-Steam game!

---

## Features

- **Mod Manager** - Scan, organize, and detect conflicts
- **Tray Browser** - View your saved Sims, Lots, and Rooms with CC tracking
- **Package Editor** - View and edit .package files
- **Profile System** - Create and switch between mod loadouts
- **Steam Deck Ready** - SD card support, touch-friendly UI

---

## System Tray

S4LT runs with a system tray icon. When you close the window, it minimizes to the tray.

**Right-click the tray icon for:**
- Open S4LT
- Restart Server
- View Logs
- Quit

---

## Requirements

- Linux x86_64 (Ubuntu 20.04+, Fedora 35+, Arch, Steam Deck, etc.)
- The Sims 4 installed via Steam/EA App/Origin

---

## Troubleshooting

**"Permission denied" when launching:**
Make sure you marked the file as executable (step 2 above).

**Window doesn't open:**
Try running from terminal: `./S4LT-0.7.0-x86_64.AppImage`
Check for error messages.

**Can't find my Mods folder:**
S4LT looks in the standard location: `~/.local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods`

If your game is installed elsewhere, S4LT will prompt you to set the path on first run.

---

## Links

- [GitHub](https://github.com/yourname/s4lt)
- [Report Issues](https://github.com/yourname/s4lt/issues)

---

*Made with love for the Sims community*
