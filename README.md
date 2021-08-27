# Archivist's Pride
A tool for monitoring supply and values of Parallel NFT wallets, card sets, etc.

![image](https://user-images.githubusercontent.com/14815901/131173186-1f173bee-44a9-493b-91de-4073901ca496.png)

# Requirements
1. Windows 10
2. Patience. (This is an alpha preview and it's a hobby project. Some things are slow right now.)

_Note: I run Windows 10. Pythong 3.9+ is **not** supported on Windows 7, so if you're keeping the dream alive, don't get your hopes up. Also, Windows 7 has been deprecated and no longer receives security fixes. But you know that and you like to live dangerously._

# Setup
1. Download the latest release from https://github.com/JERisBRISK/archivists-pride/releases. You really just need the .zip, e.g.:
   ![image](https://user-images.githubusercontent.com/14815901/131177928-2a6585ef-9cdc-4bc4-a45e-1b810232e9be.png)
3. Right-click on the archive and selec Properties. Check **Unblock** and **Apply** and/or **OK**.
4. Right-click again and **'Extract All...'** the archive into its own folder.

# Running AP
Just run **ArchivistsPride.exe** from the folder you made in **Setup**!

# Bugs
Please report any issues to https://github.com/JERisBRISK/archivists-pride/issues. Be as detailed as you can. I appreciate can't promise I'll fix them any time soon (or ever), but I hate bugs in my code so chances are high that if I can reproduce the problem, I'll get around to it.

# Testing
Note that I am a Windows 10 guy. I don't run or test AP on any other platform, so YMMV and you assume all the risks for doing so.
Python is cross-platform, so chances are good that it will work on other systems when run via Python, but I may have made some Windows-level assumptions in the code at places. Sorry for the inconvenience. If you're a developer, feel free to submit a Pull-Request and describe how your change will make things better for the world. :)


# Developer Notes
I'm fairly new to Python and DearPyGui (and ImGui for that matter). This was made on a shoestring budget (read: $0), so the level of code smell is high. It's what you might call a passion project. I wrote it for myself but drew inspiration from friends in the Parallel community which informed certain features. I hope you find it useful. Unless you're sponsoring me, I can't promise that I'll find time to service your particular problem or request, but I'll do my best as time avails.

If you wnat to run the code itself, note that `main.py` is the entry point (see `run.cmd`), and `setup.cmd` will help you install the required packages.

# Other Operating Systems
If you want to run this on another operating system, you're free to download the code and try.
You will need Python 3.9.5+. I suggest installing this one as it's what I use:
https://www.python.org/downloads/release/python-396/

# AP is dedicated with love and gratitude to
- The Parallel community. Y'all are nuts, and you're fam, and I love you. Join up at http://discord.gg/parallelalpha
- The Parallel team. See http://www.twitter.com/ParallelNFT and https://parallel.life/ to figure out what the heck this is all about.
- The DearPyGui team and its contributors. https://github.com/hoffstadt and https://github.com/Pcothren brought ImGui to Python, which lets me bring this app to you.
- Omar Cornut (https://github.com/ocornut) for ImGui, the underpinnings of DearPyGui.
- The authors of Python's many helpful packages like requests, web3, Dumper, etc.
