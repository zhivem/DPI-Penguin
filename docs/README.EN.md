# DPI Penguin [YouTube + Discord]

<img src="https://github.com/zhivem/DPI-Penguin/blob/main/resources/icon/newicon.ico" width=10% height=10%>

[![en](https://img.shields.io/badge/lang-en-red.svg)](./README.EN.md)
[![ru](https://img.shields.io/badge/lang-ru-green.svg)](./README.md)

**DPI Penguin** is a Python graphical application designed to bypass network limitations such as Deep Packet Analysis (DPI). The application provides an intuitive interface for managing scripts that allow you to access platforms such as YouTube and Discord. The application is based on integration with [Zapret](https://github.com/bol-van/zapret ). You can download the `exe` from [Releases](https://github.com/zhivem/DPI-Penguin/releases ). View the source code of the update loader `->` [Loader for DPI Penguin](https://github.com/zhivem/Loader-for-DPI-Penguin )

## Application Interface
![image](https://github.com/user-attachments/assets/8ba7ee26-1020-453a-8f23-d2c3b2dc08be)

## Features

- **User-Friendly Interface:** Created with PyQt6 for responsive and intuitive interaction.
- **Process Management:** Easily start, stop, and control scripts to bypass network restrictions.
- **System Tray Integration:** Minimize the application to the system tray for uninterrupted background operation.
- **Autostart Setup:** Option to automatically launch the application at system startup.
- **Configuration Management:** Update and reload configuration files directly from the interface.
- **Theme Support:** Toggle between light and dark themes to suit your preferences.
- **Automatic Updates:** Check for and apply updates to ensure access to the latest features.
- **Logging:** Comprehensive logging to aid in troubleshooting and monitoring application behavior.
- **DNS and Proxy:**
  - **Proxy:** The application allows you to configure, verify and apply proxy servers (`HTTP`, `HTTPS`, `SOCKS4`, `SOCKS5`) for the entire system. You can also reset the proxy settings.
  - **DNS:** Support for popular public DNS servers ('Google`, `Cloudflare', `AdGuard`, `Comss'). The user can select the interface and apply the selected DNS to improve the speed or security of the Internet.
  - **Advantages:** Changing the proxy and DNS helps to bypass blockages, speeds up the connection and increases security.

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
[DiscordFix]
executable = {ZAPRET_FOLDER}\winws.exe
args = 
    --wf-tcp=443;
    --wf-udp=443,50000-65535; 
    --filter-udp=443;
    --hostlist={BLACKLIST_FILES_1}; 
    --dpi-desync=fake; 
    --dpi-desync-udplen-increment=10;  
    --dpi-desync-repeats=6; 
    --dpi-desync-udplen-pattern=0xDEADBEEF; 
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;  
    --filter-udp=50000-65535; 
    --dpi-desync=fake;
    --dpi-desync-any-protocol;
    --dpi-desync-cutoff=d3; 
    --dpi-desync-repeats=6; 
    --dpi-desync-fake-quic={ZAPRET_FOLDER}\quic_initial_www_google_com.bin;
    --new; 
    --filter-tcp=443; 
    --hostlist={BLACKLIST_FILES_1}; 
    --dpi-desync=fake,split;
    --dpi-desync-autottl=2;  
    --dpi-desync-repeats=6; 
    --dpi-desync-fooling=badseq; 
    --dpi-desync-fake-tls={ZAPRET_FOLDER}\tls_clienthello_www_google_com.bin; 
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

MIT License. For more details, see the [LICENSE](https://github.com/zhivem/DPI-Penguin/raw/refs/heads/main/LICENSE).


