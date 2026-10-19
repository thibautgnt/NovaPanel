"""Arreter / relancer SteelSeries GG (Windows)."""
import ctypes
import subprocess
import winreg

import psutil

EXES = ["SteelSeriesGGEZ.exe", "SteelSeriesGG.exe", "SteelSeriesEngine.exe",
        "SteelSeriesPrism.exe", "SteelSeriesSonar.exe"]
RUN = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
APPROVED = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
EXE_PATH = r"C:\Program Files\SteelSeries\GG\SteelSeriesGGEZ.exe"


def running():
    names = {p.info["name"] for p in psutil.process_iter(["name"])}
    return any(exe in names for exe in EXES)


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, RUN) as k:
            winreg.QueryValueEx(k, "SteelSeriesGG")
    except OSError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, APPROVED) as k:
            val, _ = winreg.QueryValueEx(k, "SteelSeriesGG")
            return val[0] % 2 == 0  # 02 = active, 03 = desactive
    except OSError:
        return True


def set_autostart(on):
    """Comme Gestionnaire des taches > Demarrage. Demande les droits administrateur."""
    data = ("02" if on else "03") + "0" * 22
    args = f'add "HKLM\\{APPROVED}" /v SteelSeriesGG /t REG_BINARY /d {data} /f'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", "reg.exe", args, None, 0)


def stop():
    for exe in EXES:
        subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def start():
    subprocess.Popen([EXE_PATH, r"-dataPath=C:\ProgramData\SteelSeries\GG", "-dbEnv=production", "-auto=true"],
                     creationflags=subprocess.CREATE_NO_WINDOW)
