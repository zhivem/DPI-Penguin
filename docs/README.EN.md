# DPI Penguin [YouTube + Discord]

<img src="https://github.com/zhivem/DPI-Penguin/blob/main/resources/icon/newicon.ico" width=10% height=10%>

[![en](https://img.shields.io/badge/lang-en-red.svg)](./README.EN.md)
[![ru](https://img.shields.io/badge/lang-ru-green.svg)](./README.md)

**DPI Penguin** is a Python graphical application designed to bypass network limitations such as Deep Packet Analysis (DPI). The application provides an intuitive interface for managing scripts that allow you to access platforms such as YouTube and Discord. The application is based on integration with [Zapret](https://github.com/bol-van/zapret ). You can download the `exe` from [Releases](https://github.com/zhivem/DPI-Penguin/releases ). View the source code of the update loader `->` [Loader for DPI Penguin](https://github.com/zhivem/Loader-for-DPI-Penguin )

## Application Interface
![image](https://github.com/user-attachments/assets/9224d38d-ffd8-4e14-b6d2-ef8ee49d530f)
![image](https://github.com/user-attachments/assets/6144cd0e-52cd-4e4d-a167-42e2a8354a46)

## Features

- **User-Friendly Interface:** Created with PyQt6 for responsive and intuitive interaction.
- **Process Management:** Easily start, stop, and control scripts to bypass network restrictions.
- **System Tray Integration:** Minimize the application to the system tray for uninterrupted background operation.
- **Autostart Setup:** Option to automatically launch the application at system startup.
- **Configuration Management:** Update and reload configuration files directly from the interface.
- **Theme Support:** Toggle between light and dark themes to suit your preferences.
- **Automatic Updates:** Check for and apply updates to ensure access to the latest features.
- **Logging:** Comprehensive logging to aid in troubleshooting and monitoring application behavior.

## Configuration Setup

The application uses a `default.ini` file located in the `config` folder. This file contains settings for various scripts and application parameters. You can manually edit this file and add your configurations. Example based on `DiscordFix`:

### Executable Paths Should Remain Unchanged

```py
{ZAPRET_FOLDER}\winws.exe
{ZAPRET_FOLDER}\quic_initial_www_google_com.bin 
{ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin
{ZAPRET_FOLDER}\tls_clienthello_iana_org.bin
```

### Blacklist Paths Should Remain Unchanged

```py
 "russia-blacklist.txt" - {BLACKLIST_FILES_0}
 "russia-youtube.txt" - {BLACKLIST_FILES_1}
 "discord-blacklist.txt" - {BLACKLIST_FILES_2}
 "disk-youtube.txt" - {BLACKLIST_FILES_3}
 "ipset-discord.txt" - {BLACKLIST_FOLDER}\ipset-discord.txt
 "autohostlist.txt" - {BLACKLIST_FOLDER}\autohostlist.txt 
```

### DiscordFix Configuration Example

```py
[DiscordFix]  | Section name, can be named as you like
executable = {ZAPRET_FOLDER}\winws.exe | Path to the executable file for bypassing restrictions
args = 
    --wf-tcp=443;  // Open TCP port 443 (HTTPS)
    --wf-udp=443,50000-65535;  // Open UDP ports 443 and range 50000-65535
    --filter-udp=443; // Filter by UDP port 443
    --hostlist={BLACKLIST_FILES_1};  // Blocked domain list {BLACKLIST_FILES_1}
    --dpi-desync=fake;  // Use fake method to bypass DPI
    --dpi-desync-udplen-increment=10;  // Increase UDP packet length by 10 bytes
    --dpi-desync-repeats=6;  // Repeat desynchronization process 6 times
    --dpi-desync-udplen-pattern=0xDEADBEEF;  // Pattern for altering UDP packet length
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;  // Use fake QUIC traffic
    --filter-udp=50000-65535;  // Filter by UDP ports in the range 50000-65535
    --dpi-desync=fake;  // Reuse fake method for DPI bypass
    --dpi-desync-any-protocol; // Apply desynchronization to all protocols
    --dpi-desync-cutoff=d3;  // Data cutoff for additional DPI bypass
    --dpi-desync-repeats=6;  // Repeat desynchronization 6 times
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;  // Reuse fake QUIC traffic
    --new;  // Start a new session
    --filter-tcp=443;  // Filter by TCP port 443
    --hostlist={BLACKLIST_FILES_1};  // Blocked domain list {BLACKLIST_FILES_1}
    --dpi-desync=fake,split; // Fake and split packet method for DPI bypass
    --dpi-desync-autottl=2;  // Automatic TTL (Time to Live) management
    --dpi-desync-repeats=6;  // Repeat desynchronization process 6 times
    --dpi-desync-fooling=badseq; // Fool DPI with incorrect packet sequence
    --dpi-desync-fake-tls={ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin;  // Use fake TLS traffic
```

### Additional Configuration Files

The program archive contains configurations you can use instead of the regular `default.ini: DiscordFix (for MGTS).ini`, `YoutubeFix (for MGTS).ini`, `FixYouTube+Discord (for Beeline, Rostelecom, Infolink).ini`, etc. To open the configuration folder, click the `Open configs button`.

### Possible Errors

- If the Start button is unresponsive, there is likely an error in the configuration, which should display in the text field.
- Duplicate configuration names are not allowed; otherwise, the program will display an error.

## Theme Usage

You can edit `.qss` files in the `.._internal\resources\styles` folder according to your preferences if you dislike the default program interface.

```py
dark_theme.qss - dark interface
light_theme.qss - light interface
```

## Installation

For those who do not want to build the project and make modifications, download the archive from the [Releases](https://github.com/zhivem/DPI-Penguin/releases), tab. For those who want to build their own version:

1. Clone the repository:

    ```bash
    git clone https://github.com/zhivem/DPI-Penguin.git 
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Run the application:

    ```bash
    python main.py
    ```

## Acknowledgements

- **GoodbyeDPI:** Foundation for YouTube operation. Developer: ValdikSS. [Repository](https://github.com/ValdikSS/GoodbyeDPI)
- **Zapret:** Foundation for Discord and YouTube operation. Developer: bol-van. [Repository](https://github.com/bol-van/zapret)

## License 

This project is licensed under the [Apache License, Version 2.0.](https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/LICENSE.md)

