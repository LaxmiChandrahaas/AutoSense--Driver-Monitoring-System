@"
# 🚗 Driver Monitoring System (DMS)

A real‑time driver drowsiness detection system built with **Python**, **OpenCV**, and **MediaPipe Tasks API**.  
It monitors eye closure, blink patterns, yawning, and head posture using a standard webcam, and displays a live dashboard with fatigue indicators.

---

## 📸 Live Demo

<video src="demo.mp4" controls width="100%" autoplay muted loop>
  Your browser does not support the video tag. 
  <a href="demo.mp4">Download demo.mp4</a>
</video>

*The system runs at ~15‑20 FPS on a laptop webcam. All metrics update in real time.*

---

## ✨ Features

- **Eye Aspect Ratio (EAR)** based drowsiness detection  
- **Blink counting** (detects rapid eye closure)  
- **Yawn detection** via Mouth Aspect Ratio (MAR)  
- **Head‑down posture detection** (tilt estimation)  
- **Fatigue percentage** – computed from EAR moving average  
- **Live dashboard overlay** showing:
  - EAR value
  - Blink count
  - Yawn count
  - Fatigue level (%)
  - Status: `AWAKE`, `DROWSY`, or `HEAD DOWN`
  - Session timer
- **Audio alerts** (optional – easily extendable)  
- **Modular code** – ready for hardware/IoT integration

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.7+ |
| Computer Vision | OpenCV |
| Face Landmarks | MediaPipe (Tasks API) |
| Mathematical computations | NumPy |
| (Optional) IoT | Raspberry Pi, MQTT, GPIO |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- A working webcam
- (Optional) Git

### 1. Clone the repository

```bash
git clone https://github.com/LaxmiChandrahaas/Driver-Monitoring-System.git
cd Driver-Monitoring-System
