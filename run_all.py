"""
Single-command runner for the Driver Monitor + Wokwi Pico simulation.

Prerequisite (one-time, per simulator session — this part can't be
triggered from a terminal, since it's a VS Code editor action):
    Command Palette (Ctrl+Shift+P) -> "Wokwi: Start Simulator"
    Keep that simulator tab visible/open.

Then, from this folder, run just:
    python run_all.py

This single command will:
    1. Install mpremote if it's missing
    2. Wait for the simulator's RFC2217 bridge (localhost:4000)
    3. Upload main.py to the simulated Pico and reboot it
    4. Launch driver_monitor.py (your webcam/OpenCV script)
"""

import socket
import subprocess
import sys
import time

RFC2217_HOST = "localhost"
RFC2217_PORT = 4000
CONNECT_RETRIES = 20
RETRY_DELAY_SECONDS = 1


def ensure_mpremote_installed():
    try:
        subprocess.run(
            [sys.executable, "-m", "mpremote", "version"],
            check=True,
            capture_output=True,
        )
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("mpremote not found — installing it now...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "mpremote"],
        check=True,
    )


def wait_for_simulator():
    print(f"Waiting for the Wokwi simulator on {RFC2217_HOST}:{RFC2217_PORT} ...")
    for attempt in range(1, CONNECT_RETRIES + 1):
        try:
            with socket.create_connection((RFC2217_HOST, RFC2217_PORT), timeout=1):
                print("Simulator is up.")
                return True
        except OSError:
            if attempt == CONNECT_RETRIES:
                return False
            time.sleep(RETRY_DELAY_SECONDS)
    return False


def upload_and_reset():
    print("Uploading main.py to the simulated Pico...")
    result = subprocess.run(
        [
            sys.executable, "-m", "mpremote",
            "connect", f"port:rfc2217://{RFC2217_HOST}:{RFC2217_PORT}",
            "fs", "cp", "main.py", ":main.py",
            "+",
            "soft-reset",
        ]
    )
    return result.returncode == 0


def run_driver_monitor():
    print("\nStarting driver_monitor.py — your webcam window should open shortly.\n")
    subprocess.run([sys.executable, "driver_monitor.py"])


def main():
    ensure_mpremote_installed()

    if not wait_for_simulator():
        print(
            "\n❌ Could not reach the Wokwi simulator.\n"
            '   Start it first: Command Palette -> "Wokwi: Start Simulator",\n'
            "   keep its tab visible, then re-run: python run_all.py"
        )
        sys.exit(1)

    if not upload_and_reset():
        print(
            "\n❌ Firmware upload failed. Make sure the simulator tab is\n"
            "   still open and visible, then re-run: python run_all.py"
        )
        sys.exit(1)

    print("✅ Firmware uploaded and board reset.")
    run_driver_monitor()


if __name__ == "__main__":
    main()
