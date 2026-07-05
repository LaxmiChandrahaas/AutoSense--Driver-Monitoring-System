import cv2
import math
import time
import sys
from collections import deque
import serial

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- GLOBAL SHARED VARIABLES FOR THREADING ---
latest_landmarks = None
EAR_THRESHOLD = 0.25
CONSEC_FRAMES_FOR_ALERT = 15
YAWN_THRESHOLD = 0.65
model_path = "face_landmarker.task"

# --- HARDWARE TARGET CONFIGURATION ---
# Set to True to drive a Wokwi simulation (Raspberry Pi Pico) instead of a
# real board. This connects to the RFC2217 server that "Wokwi for VS Code"
# starts when rfc2217ServerPort is set in wokwi.toml, and the running
# simulation tab is open.
USE_WOKWI_SIMULATOR = True
WOKWI_RFC2217_URL = "rfc2217://localhost:4000"
REAL_SERIAL_PORT = "COM3"
BAUD_RATE = 115200

# --- SERIAL / SIMULATOR CONNECTION PIPELINE ---
pico = None
try:
    if USE_WOKWI_SIMULATOR:
        pico = serial.serial_for_url(WOKWI_RFC2217_URL, baudrate=BAUD_RATE, timeout=0.1)
        print("⚡ Connected to Wokwi simulator (Raspberry Pi Pico) via RFC2217!")
    else:
        pico = serial.Serial(port=REAL_SERIAL_PORT, baudrate=BAUD_RATE, timeout=0.1)
        print("⚡ Connected to real hardware on", REAL_SERIAL_PORT)
except Exception as e:
    print(f"⚠️ Could not connect to board/simulator ({e}). Running in UI-only mode.")
    pico = None

# --- ASYNC CALLBACK FUNCTION ---
def print_result(result: vision.FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_landmarks
    if result and result.face_landmarks:
        latest_landmarks = result.face_landmarks[0]
    else:
        latest_landmarks = None

# --- MEDIAPIPE LIVE STREAM INITIALIZATION ---
base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1,
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=print_result
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# --- SAFE COORDINATE CONVERSION ---
def get_coords(landmark, shape):
    h, w, _ = shape
    return int(landmark.x * w), int(landmark.y * h)

def euclidean(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def eye_aspect_ratio(landmarks, shape):
    left_eye = [33, 160, 158, 133, 153, 144]
    right_eye = [362, 385, 387, 263, 373, 380]
    def ear_for(pts):
        p = [get_coords(landmarks[i], shape) for i in pts]
        return (euclidean(p[1], p[5]) + euclidean(p[2], p[4])) / (2.0 * max(0.001, euclidean(p[0], p[3])))
    return (ear_for(left_eye) + ear_for(right_eye)) / 2.0

def mouth_aspect_ratio(landmarks, shape):
    upper = get_coords(landmarks[13], shape)
    lower = get_coords(landmarks[14], shape)
    left = get_coords(landmarks[61], shape)
    right = get_coords(landmarks[291], shape)
    return euclidean(upper, lower) / max(0.001, euclidean(left, right))

def head_down_score(landmarks, shape):
    nose = get_coords(landmarks[1], shape)
    left_eye = get_coords(landmarks[33], shape)
    right_eye = get_coords(landmarks[263], shape)
    return nose[1] - ((left_eye[1] + right_eye[1]) / 2)

# --- HEADS UP DISPLAY DESIGN ---
def draw_dashboard(frame, ear, blinks, yawns, fatigue, status, elapsed_sec):
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (280, 190), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, "DRIVER MONITOR SYSTEM", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    metrics = [f"EAR: {ear:.2f}", f"Blinks: {blinks}", f"Yawns: {yawns}", f"Fatigue: {fatigue}%"]
    for i, txt in enumerate(metrics):
        cv2.putText(frame, txt, (20, 75 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    color = (0, 255, 0) if status == "AWAKE" else (0, 0, 255)
    cv2.putText(frame, f"Status: {status}", (20, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

# --- MAIN LOOP ---
def main():
    global latest_landmarks
    # CAP_DSHOW is a Windows-only backend; use the platform default elsewhere
    # so this runs correctly on macOS/Linux too.
    camera_backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(0, camera_backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Camera initialization error.")
        return

    window_name = "Driver Monitor System"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    blink_counter = 0
    yawn_counter = 0
    eye_closed_frames = 0
    was_eye_closed = False
    was_yawning = False
    ear_history = deque(maxlen=30)

    ear, mar, head_down = 0.0, 0.0, 0
    status = "AWAKE"
    fatigue = 0
    last_sent_status = None

    start_time = time.time()
    print("🚀 Running Error-Protected Stream loop...")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            cv2.waitKey(5)
            continue

        frame = cv2.flip(frame, 1)
        small_frame = cv2.resize(frame, (320, 240))
        rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Ship frame to background analysis thread
        timestamp_ms = int((time.time() - start_time) * 1000)
        try:
            landmarker.detect_async(mp_image, timestamp_ms)
        except Exception:
            pass

        # --- PROTECTED CALCULATION BLOCK ---
        if latest_landmarks is not None:
            try:
                shape = small_frame.shape
                ear = eye_aspect_ratio(latest_landmarks, shape)
                mar = mouth_aspect_ratio(latest_landmarks, shape)
                head_down = head_down_score(latest_landmarks, shape)

                if ear < EAR_THRESHOLD:
                    eye_closed_frames += 1
                    was_eye_closed = True
                else:
                    if was_eye_closed and eye_closed_frames >= 3:
                        blink_counter += 1
                    was_eye_closed = False
                    eye_closed_frames = 0

                if mar > YAWN_THRESHOLD:
                    if not was_yawning:
                        yawn_counter += 1
                        was_yawning = True
                else:
                    was_yawning = False

                ear_history.append(ear)
                if len(ear_history) > 10:
                    avg_ear = sum(ear_history) / len(ear_history)
                    fatigue = max(0, min(100, int((1 - avg_ear / 0.30) * 100)))

                if ear < EAR_THRESHOLD and eye_closed_frames > CONSEC_FRAMES_FOR_ALERT:
                    status = "DROWSY"
                    new_code = "D"
                elif head_down > 25:
                    status = "HEAD DOWN"
                    new_code = "H"
                else:
                    status = "AWAKE"
                    new_code = "A"

                # Only write to serial when the state actually changes,
                # to avoid flooding the simulated USB-serial link.
                if pico and new_code != last_sent_status:
                    pico.write(new_code.encode())
                    last_sent_status = new_code
            except Exception as calc_error:
                print(f"⚠️ Calculation Error caught safely: {calc_error}")

        elapsed = time.time() - start_time
        draw_dashboard(frame, ear, blink_counter, yawn_counter, fatigue, status, elapsed)

        cv2.imshow(window_name, frame)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    if pico:
        pico.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()