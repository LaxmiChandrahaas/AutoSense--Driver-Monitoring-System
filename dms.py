import cv2
import math
import time
from collections import deque

# ============================================
# NEW: MediaPipe Tasks API (instead of solutions)
# ============================================
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ============================================
# CONFIGURATION
# ============================================
EAR_THRESHOLD = 0.25
CONSEC_FRAMES_FOR_ALERT = 15
YAWN_THRESHOLD = 0.65

# ============================================
# INITIALIZE FACE LANDMARKER (Tasks API)
# ============================================
model_path = "face_landmarker.task"
# If the above path doesn't work, you can download the model manually:
# https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1,
    running_mode=vision.RunningMode.IMAGE
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# ============================================
# HELPER FUNCTIONS (same as before)
# ============================================
def get_coords(landmark, shape):
    h, w, _ = shape
    return int(landmark.x * w), int(landmark.y * h)

def euclidean(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def eye_aspect_ratio(landmarks, shape):
    # landmarks is a list of 478 normalized landmarks
    left_eye = [33, 160, 158, 133, 153, 144]
    right_eye = [362, 385, 387, 263, 373, 380]

    def ear_for(pts):
        p = [get_coords(landmarks[i], shape) for i in pts]
        v1 = euclidean(p[1], p[5])
        v2 = euclidean(p[2], p[4])
        h = euclidean(p[0], p[3])
        return (v1 + v2) / (2.0 * h)

    return (ear_for(left_eye) + ear_for(right_eye)) / 2.0

def mouth_aspect_ratio(landmarks, shape):
    upper = get_coords(landmarks[13], shape)
    lower = get_coords(landmarks[14], shape)
    left = get_coords(landmarks[61], shape)
    right = get_coords(landmarks[291], shape)
    vert = euclidean(upper, lower)
    horz = euclidean(left, right)
    return vert / horz

def head_down_score(landmarks, shape):
    nose = get_coords(landmarks[1], shape)
    left_eye = get_coords(landmarks[33], shape)
    right_eye = get_coords(landmarks[263], shape)
    eye_avg_y = (left_eye[1] + right_eye[1]) / 2
    return nose[1] - eye_avg_y

# ============================================
# DASHBOARD DRAWING (identical)
# ============================================
def draw_dashboard(frame, ear, blinks, yawns, fatigue, status, elapsed_sec):
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (280, 190), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, "DRIVER MONITOR SYSTEM", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    y0 = 75
    line_h = 30
    metrics = [
        f"EAR: {ear:.2f}",
        f"Blinks: {blinks}",
        f"Yawns: {yawns}",
        f"Fatigue: {fatigue}%"
    ]
    for i, txt in enumerate(metrics):
        cv2.putText(frame, txt, (20, y0 + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    color = (0, 255, 0) if status == "AWAKE" else (0, 0, 255)
    cv2.putText(frame, f"Status: {status}", (20, y0 + 4 * line_h),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    mins = int(elapsed_sec // 60)
    secs = int(elapsed_sec % 60)
    timer_str = f"{mins:02d}:{secs:02d}    1x"
    (tw, th), _ = cv2.getTextSize(timer_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    cv2.putText(frame, timer_str, (w - tw - 20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

# ============================================
# MAIN LOOP (with Tasks API)
# ============================================
def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("❌ Cannot open camera.")
        return

    blink_counter = 0
    yawn_counter = 0
    eye_closed_frames = 0
    was_eye_closed = False
    was_yawning = False
    ear_history = deque(maxlen=30)

    start_time = time.time()
    print("✅ Camera started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert frame to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Detect face landmarks
        detection_result = landmarker.detect(mp_image)
        landmarks = detection_result.face_landmarks[0] if detection_result.face_landmarks else None

        ear, mar, head_down = 0.0, 0.0, 0
        status = "AWAKE"
        fatigue = 0

        if landmarks:
            shape = frame.shape
            ear = eye_aspect_ratio(landmarks, shape)
            mar = mouth_aspect_ratio(landmarks, shape)
            head_down = head_down_score(landmarks, shape)

            # Blink
            if ear < EAR_THRESHOLD:
                eye_closed_frames += 1
                was_eye_closed = True
            else:
                if was_eye_closed and eye_closed_frames >= 3:
                    blink_counter += 1
                was_eye_closed = False
                eye_closed_frames = 0

            # Yawn
            if mar > YAWN_THRESHOLD:
                if not was_yawning:
                    yawn_counter += 1
                    was_yawning = True
            else:
                was_yawning = False

            # Fatigue
            ear_history.append(ear)
            if len(ear_history) > 10:
                avg_ear = sum(ear_history) / len(ear_history)
                fatigue = max(0, min(100, int((1 - avg_ear / 0.30) * 100)))

            # Status
            if ear < EAR_THRESHOLD and eye_closed_frames > CONSEC_FRAMES_FOR_ALERT:
                status = "DROWSY"
            elif head_down > 25:
                status = "HEAD DOWN"
            else:
                status = "AWAKE"

        elapsed = time.time() - start_time
        draw_dashboard(frame, ear, blink_counter, yawn_counter, fatigue, status, elapsed)

        cv2.imshow("Driver Monitor System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()