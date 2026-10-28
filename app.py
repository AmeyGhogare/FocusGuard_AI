
import csv
import os
import threading
import time
from pathlib import Path

import cv2
import mediapipe as mp

from flask import Flask, Response, jsonify, render_template

from vision.face_landmarks import (
    AttentionEngine,
    calculate_ear,
    draw_eye,
    estimate_head_pose,
    LEFT_EYE,
    RIGHT_EYE,
    EAR_THRESHOLD,
    MIN_BLINK_SECONDS,
    MAX_BLINK_SECONDS,
)
from vision.session_tracker import SessionTracker


app = Flask(__name__)

# ==========================================
# CONFIGURATION
# ==========================================

SESSIONS_DIR = Path("data") / "sessions"

lock = threading.Lock()
stop_event = threading.Event()

camera_thread = None
latest_frame = None
monitoring = False

stats = {
    "state": "Unknown",
    "duration_seconds": 0,
    "focus_percentage": 0,
    "blink_count": 0,
    "distraction_events": 0,
    "eye_closure_events": 0,
    "focused_seconds": 0,
    "distracted_seconds": 0,
    "eye_closure_seconds": 0,
    "unknown_seconds": 0,
    "pitch": None,
    "yaw": None,
    "roll": None,
    "message": "Monitoring stopped",
}


# ==========================================
# WEBCAM MONITORING
# ==========================================

def camera_worker():
    global latest_frame, monitoring, stats

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        camera.release()

        with lock:
            monitoring = False
            stats["state"] = "Unknown"
            stats["message"] = "Could not open webcam"

        return

    mp_face_mesh = mp.solutions.face_mesh

    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    attention_engine = AttentionEngine()
    tracker = SessionTracker()

    blink_count = 0
    eyes_closed = False
    closed_start = None

    try:
        while not stop_event.is_set():
            success, frame = camera.read()

            if not success:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            now = time.monotonic()

            state = "Unknown"
            pitch = None
            yaw = None
            roll = None

            if results.multi_face_landmarks:
                face = results.multi_face_landmarks[0]
                landmarks = face.landmark

                left_ear, left_points = calculate_ear(
                    landmarks, LEFT_EYE, width, height
                )

                right_ear, right_points = calculate_ear(
                    landmarks, RIGHT_EYE, width, height
                )

                draw_eye(frame, left_points)
                draw_eye(frame, right_points)

                average_ear = (left_ear + right_ear) / 2.0
                eyes_open = average_ear >= EAR_THRESHOLD

                # Count completed blinks.
                if not eyes_open:
                    if not eyes_closed:
                        closed_start = now

                    eyes_closed = True

                else:
                    if eyes_closed and closed_start is not None:
                        blink_duration = now - closed_start

                        if (
                            MIN_BLINK_SECONDS
                            <= blink_duration
                            <= MAX_BLINK_SECONDS
                        ):
                            blink_count += 1

                    eyes_closed = False
                    closed_start = None

                pose = estimate_head_pose(
                    landmarks, width, height
                )

                if pose is not None:
                    pitch, yaw, roll = pose

                    state = attention_engine.update(
                        eyes_open=eyes_open,
                        pitch=pitch,
                        yaw=yaw,
                        now=now,
                    )
                else:
                    state = attention_engine.update(
                        eyes_open=None,
                        pitch=None,
                        yaw=None,
                        now=now,
                    )

                mp.solutions.drawing_utils.draw_landmarks(
                    image=frame,
                    landmark_list=face,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=(
                        mp.solutions.drawing_styles
                        .get_default_face_mesh_contours_style()
                    ),
                )

                cv2.putText(
                    frame,
                    f"Left EAR: {left_ear:.3f}",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Right EAR: {right_ear:.3f}",
                    (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2,
                )

            else:
                attention_engine.update(
                    eyes_open=None,
                    pitch=None,
                    yaw=None,
                    now=now,
                )

                eyes_closed = False
                closed_start = None

                cv2.putText(
                    frame,
                    "No face detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            # Update session analytics.
            tracker.update(state)
            summary = tracker.get_summary()

            cv2.putText(
                frame,
                f"Attention: {state}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 130, 0) if state == "Focused" else (0, 0, 255),
                2,
            )

            cv2.putText(
                frame,
                f"Blinks: {blink_count}",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
            )

            encoded, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80],
            )

            if encoded:
                with lock:
                    latest_frame = buffer.tobytes()

                    stats.update({
                        "state": state,
                        "duration_seconds": summary["duration_seconds"],
                        "focus_percentage": summary["focus_percentage"],
                        "blink_count": blink_count,
                        "distraction_events": summary["distraction_events"],
                        "eye_closure_events": summary["eye_closure_events"],
                        "focused_seconds": summary["focused_seconds"],
                        "distracted_seconds": summary["distracted_seconds"],
                        "eye_closure_seconds": summary["eye_closure_seconds"],
                        "unknown_seconds": summary["unknown_seconds"],
                        "pitch": round(pitch, 1) if pitch is not None else None,
                        "yaw": round(yaw, 1) if yaw is not None else None,
                        "roll": round(roll, 1) if roll is not None else None,
                        "message": "Monitoring active",
                    })

    except Exception as error:
        print("Webcam monitoring error:", error)

        with lock:
            stats["message"] = f"Monitoring error: {error}"

    finally:
        camera.release()
        face_mesh.close()

        try:
            tracker.update(attention_engine.current_state)
            file_path = tracker.save_csv(str(SESSIONS_DIR))
            summary = tracker.get_summary()

            with lock:
                stats.update(summary)
                stats["blink_count"] = blink_count
                stats["csv_file"] = os.path.basename(file_path)
                stats["message"] = "Session saved"

        except (OSError, csv.Error) as error:
            with lock:
                stats["message"] = f"Could not save session: {error}"

        with lock:
            monitoring = False
            latest_frame = None


# ==========================================
# DASHBOARD ROUTES
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global camera_thread, monitoring, stats

    with lock:
        if monitoring:
            return jsonify({
                "success": True,
                "message": "Monitoring is already active",
            })

        if camera_thread is not None and camera_thread.is_alive():
            return jsonify({
                "success": False,
                "message": "The previous session is still shutting down",
            }), 409

        stop_event.clear()
        latest_state = "Unknown"
        monitoring = True

        stats = {
            "state": latest_state,
            "duration_seconds": 0,
            "focus_percentage": 0,
            "blink_count": 0,
            "distraction_events": 0,
            "eye_closure_events": 0,
            "focused_seconds": 0,
            "distracted_seconds": 0,
            "eye_closure_seconds": 0,
            "unknown_seconds": 0,
            "pitch": None,
            "yaw": None,
            "roll": None,
            "message": "Starting monitoring",
        }

        camera_thread = threading.Thread(
            target=camera_worker,
            daemon=True,
        )
        camera_thread.start()

    return jsonify({
        "success": True,
        "message": "Monitoring started",
    })


@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    if not monitoring:
        with lock:
            message = stats.get("message", "Monitoring is not active")

        return jsonify({
            "success": True,
            "message": message,
        })

    stop_event.set()

    return jsonify({
        "success": True,
        "message": "Stopping monitoring and saving session",
    })


@app.route("/api/stats")
def get_stats():
    with lock:
        current_stats = stats.copy()
        current_stats["monitoring"] = monitoring

    return jsonify(current_stats)


@app.route("/video_feed")
def video_feed():
    def generate_frames():
        while True:
            with lock:
                frame = latest_frame
                active = monitoring

            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )

            elif not active:
                time.sleep(0.1)

            else:
                time.sleep(0.03)

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ==========================================
# SESSION HISTORY API
# ==========================================

@app.route("/api/history")
def session_history():
    sessions = []

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in SESSIONS_DIR.glob("session_*.csv"):
        try:
            with file_path.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as file:
                reader = csv.DictReader(file)

                for row in reader:
                    row["csv_file"] = file_path.name
                    sessions.append(row)

        except (OSError, csv.Error) as error:
            print("Could not read", file_path.name, ":", error)

    sessions.sort(
        key=lambda row: row.get("session_id", ""),
        reverse=True,
    )

    return jsonify({"sessions": sessions})


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )
