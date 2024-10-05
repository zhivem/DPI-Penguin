import os
import platform

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "icon")

BLACKLIST_FILES = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt")
]

GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, "bin", platform.machine(), "goodbyedpi.exe")
WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]
GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

CURRENT_VERSION = "1.2"
