# S4LT - Sims 4 Mod Manager for Steam Deck & Linux

**Finally, a mod manager that works natively on Linux!**

S4LT (Sims 4 Linux Toolkit) is a free, open-source mod manager designed specifically for Steam Deck and Linux users. No terminal commands needed - everything works with clicks!

---

## What It Does

- **Automatically finds your mods** - Works with NonSteamLaunchers, Steam, Heroic, Lutris
- **Categorizes your CC** - Script Mods, CAS CC, Build/Buy CC, Tuning Mods
- **Enable/Disable mods easily** - Simple toggle switches, no file renaming
- **Vanilla Mode** - One click to play without mods
- **Detect conflicts** - Find mods that override each other
- **Manage profiles** - Switch between different mod setups

---

## Installation (3 Steps!)

### Step 1: Download
Download `S4LT-0.8.0-x86_64.AppImage` from the files section.

### Step 2: Make Executable
Right-click the file → Properties → Permissions → Check "Allow executing as program"

### Step 3: Run
Double-click the AppImage to launch S4LT!

**That's it!** On first run, S4LT will automatically detect your mods folder.

---

## Steam Deck Specific

S4LT is optimized for Steam Deck:

- **Touch-friendly interface** - Big buttons, easy scrolling
- **Auto-detects NonSteamLaunchers** - Works out of the box
- **SD card support** - Manage mods on external storage

**Your Mods path (NonSteamLaunchers):**
```
/home/deck/.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods/
```

If S4LT doesn't find your mods automatically, you can paste this path in the setup wizard.

---

## Features

### Dashboard
See your mod counts at a glance:
- Total mods
- Script Mods (MCCC, Wicked Whims, etc.)
- CAS CC (hair, clothes, makeup)
- Build/Buy CC (furniture, decor)
- Broken mods

### Mod Browser
- Toggle mods on/off with a switch
- Search and filter by category
- View mod details

### Profiles
- Save your current mod setup
- Load different configurations
- Great for testing or different playstyles

### Vanilla Mode
- One click to disable ALL mods
- Perfect for testing if mods cause crashes
- Restores mods when you toggle back

---

## Frequently Asked Questions

**Q: Does this work with [mod name]?**
A: S4LT works with ALL .package files. It doesn't modify mods, just helps you manage them.

**Q: Will this break my mods?**
A: No. S4LT only renames files (adds/removes .disabled extension). Your mods stay exactly the same.

**Q: I don't see my mods folder**
A: Go to Settings and paste your mods path manually. See the "Steam Deck Specific" section above for common paths.

**Q: The icon shows as a green diamond**
A: This is the fallback icon. The app works fine - it just couldn't find the icon file.

---

## Support

- **Bug reports:** [GitHub Issues](https://github.com/YOUR_USERNAME/s4lt/issues)
- **Source code:** [GitHub](https://github.com/YOUR_USERNAME/s4lt)

---

## Credits

Created for the Sims 4 modding community.
Special thanks to everyone who helped test on Steam Deck!

---

**License:** MIT (Free and open source)
**Version:** 0.8.0
**Platform:** Linux / Steam Deck
