# 🚗💤 AutoSense - Driver Monitoring System — OpenCV + Raspberry Pi Pico (Wokwi Simulation)

A real-time driver drowsiness and distraction detection system. A webcam
feed is analyzed with **OpenCV** and **MediaPipe Face Landmarker** to track
eye closure, yawning, and head pose — and the resulting status is sent
over serial to a **Raspberry Pi Pico**, simulated entirely in **Wokwi**,
which drives LED indicators and a buzzer alert.

No physical hardware is required — the Pico, LEDs, and buzzer all run in
simulation, wired up to your real, local Python vision pipeline.

---

## ✨ Features

- Real-time eye aspect ratio (EAR) tracking → blink counting & drowsy-eye detection
- Mouth aspect ratio (MAR) tracking → yawn counting
- Head-pose estimation → detects "head down" / distracted posture
- Live fatigue score (0–100%)
- On-screen dashboard overlay (EAR, blink/yawn counts, fatigue %, status)
- Status codes streamed over serial to a simulated Raspberry Pi Pico:
  - 🟢 **Awake** → green LED
  - 🟡 **Head down** → yellow LED + warning tone
  - 🔴 **Drowsy** → red LED + alarm tone
- Works with either the Wokwi simulator or a real physical Pico (one config flag)

---

## 🧩 How it works

```
Webcam ──▶ OpenCV + MediaPipe ──▶ EAR / MAR / head-pose ──▶ Status (A/H/D)
                                                                  │
                                                         serial (RFC2217)
                                                                  │
                                                                  ▼
                                          Simulated Raspberry Pi Pico (Wokwi)
                                          ──▶ LEDs + buzzer react live
```

---

## 🖥️ Try it live (no install — hardware only)

Want to see the embedded side in action without setting anything up?

👉 **[Open the live Wokwi simulation](#)** *(replace with your Wokwi
project's share link — click SAVE then SHARE in the Wokwi editor to get one)*

Click ▶ **Play**, then type `A`, `H`, or `D` into the console and press
Enter to see the LEDs/buzzer react. Note: this browser demo can't connect
to a real webcam or `driver_monitor.py` — see below to run the full
pipeline.

---

## 🚀 Run the full project locally

### Prerequisites

- [Python 3.9+](https://www.python.org/downloads/)
- [VS Code](https://code.visualstudio.com/)
- [Wokwi for VS Code](https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode) extension (free license — activate via `Wokwi: Request a new License` in the Command Palette)
- A webcam

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download two required files (not included in the repo)

| File | Download link | Save as |
|---|---|---|
| MicroPython firmware for the Pico | [rp2-pico-latest.uf2](https://micropython.org/download/rp2-pico/rp2-pico-latest.uf2) | `firmware.uf2` |
| MediaPipe face landmark model | [face_landmarker.task](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task) | `face_landmarker.task` |

Place both directly in the project folder.

### 4. Open the folder in VS Code

```bash
code .
```

### 5. Start the Wokwi simulator

`Ctrl+Shift+P` → **"Wokwi: Start Simulator"** → keep that tab visible.

### 6. Run everything with one command

```bash
python run_all.py
```

This installs `mpremote` if needed, waits for the simulator, uploads the
firmware, reboots the board, and launches your webcam script — all in one
step. You should see the Wokwi Terminal print:

```
Pico driver-monitor firmware ready (USB). Waiting for A/H/D bytes...
```

...followed by your webcam window opening. Move your head down or close
your eyes for a few seconds to trigger the alerts.

> Editing `main.py` only? Run `python upload_firmware.py` instead to
> re-upload without relaunching the webcam script.

---

## 📁 Project structure

```
.
├── diagram.json          # Wokwi circuit: Pico + 3 LEDs + buzzer
├── main.py                # MicroPython firmware (runs on the simulated Pico)
├── wokwi.toml             # Wokwi/VS Code project config (RFC2217 serial bridge)
├── driver_monitor.py       # Main OpenCV/MediaPipe drowsiness detection script
├── upload_firmware.py      # Uploads main.py to the running simulator
├── run_all.py              # Upload firmware + launch driver_monitor.py in one step
├── requirements.txt        # Python dependencies
├── firmware.uf2            # (you download this — see step 3)
└── face_landmarker.task    # (you download this — see step 3)
```

---

## 🔌 Wiring (as modeled in `diagram.json`)

| Pico pin | Component                | Purpose             |
|----------|---------------------------|---------------------|
| GP16     | 220 Ω → Green LED → GND    | Awake indicator     |
| GP17     | 220 Ω → Yellow LED → GND   | Head-down indicator |
| GP18     | 220 Ω → Red LED → GND      | Drowsy indicator    |
| GP19     | Buzzer → GND               | Audible alert       |

## 📡 Status codes

| Code | Meaning   | LED    | Buzzer       |
|------|-----------|--------|--------------|
| `A`  | Awake     | Green  | Off          |
| `H`  | Head down | Yellow | 600 Hz tone  |
| `D`  | Drowsy    | Red    | 1200 Hz tone |

---

## 🔧 Switching to real hardware

Have an actual Raspberry Pi Pico? In `driver_monitor.py`, change:

```python
USE_WOKWI_SIMULATOR = False
REAL_SERIAL_PORT = "COM3"  # or your Pico's actual port
```

No other changes are needed — both paths send the same `A`/`H`/`D` bytes
over serial. Flash `main.py` to the real board the normal way (e.g. via
Thonny or `mpremote`).

---

## 🛠️ Troubleshooting

| Symptom | Fix |
|---|---|
| `Firmware path must be a string` | Make sure `firmware.uf2` exists in the project folder and `wokwi.toml` points to it |
| Diagram shows no wiring / no Play button | The file must be named exactly `diagram.json`, no variants like `diagram (1).json` |
| Board stuck at `>>>`, LEDs don't respond | Firmware crashed or was never uploaded — restart the simulator and re-run `python run_all.py` |
| `[WinError 10061] connection refused` on port 4000 | Simulator isn't running yet — start it *before* running any Python script |
| `could not enter raw repl` during upload | Fully restart the simulator (stop, then start again), then re-run `python run_all.py` |
| `FileNotFoundError: face_landmarker.task` | That file must sit in the project folder — see step 3 |
| Buzzer lights up but makes no sound | Check `diagram.json`'s buzzer `"volume"` is set to `"1"`, check system volume isn't muted, and click inside the simulator once (browsers block audio until a user interaction) |

---
