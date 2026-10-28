
import cv2
import mediapipe as mp
import numpy as np
import math
import time

from vision.session_tracker import SessionTracker


# ==========================================
# CONFIGURATION
# ==========================================

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

EAR_THRESHOLD = 0.21
MIN_BLINK_SECONDS = 0.04
MAX_BLINK_SECONDS = 0.40

EYE_CLOSED_THRESHOLD = 1.5
LOOK_AWAY_THRESHOLD = 2.0
MAX_YAW = 25.0
MAX_PITCH = 20.0


# ==========================================
# ATTENTION STATE ENGINE
# ==========================================

class AttentionEngine:

    def __init__(self):
        self.eye_closed_start = None
        self.look_away_start = None
        self.current_state = "Unknown"

    def update(self, eyes_open, pitch, yaw, now):

        if eyes_open is None or pitch is None or yaw is None:
            self.eye_closed_start = None
            self.look_away_start = None
            self.current_state = "Unknown"
            return self.current_state

        # Track eye closure duration
        if not eyes_open:
            if self.eye_closed_start is None:
                self.eye_closed_start = now
        else:
            self.eye_closed_start = None

        # Track sustained head movement away from the screen
        looking_away = (
            abs(yaw) > MAX_YAW
            or abs(pitch) > MAX_PITCH
        )

        if looking_away:
            if self.look_away_start is None:
                self.look_away_start = now
        else:
            self.look_away_start = None

        # Determine the estimated attention state
        if (
            self.eye_closed_start is not None
            and now - self.eye_closed_start >= EYE_CLOSED_THRESHOLD
        ):
            self.current_state = "Prolonged Eye Closure"

        elif (
            self.look_away_start is not None
            and now - self.look_away_start >= LOOK_AWAY_THRESHOLD
        ):
            self.current_state = "Possibly Distracted"

        else:
            self.current_state = "Focused"

        return self.current_state


# ==========================================
# DISTANCE CALCULATION
# ==========================================

def distance(point1, point2):
    return math.sqrt(
        (point1[0] - point2[0]) ** 2
        + (point1[1] - point2[1]) ** 2
    )


# ==========================================
# EYE ASPECT RATIO
# ==========================================

def calculate_ear(landmarks, eye_indices, width, height):

    points = []

    for index in eye_indices:
        landmark = landmarks[index]
        x = int(landmark.x * width)
        y = int(landmark.y * height)
        points.append((x, y))

    vertical1 = distance(points[1], points[5])
    vertical2 = distance(points[2], points[4])
    horizontal = distance(points[0], points[3])

    if horizontal == 0:
        return 0.0, points

    ear = (vertical1 + vertical2) / (2.0 * horizontal)

    return ear, points


# ==========================================
# DRAW EYE LANDMARKS
# ==========================================

def draw_eye(frame, points):

    for point in points:
        cv2.circle(frame, point, 2, (0, 255, 255), -1)

    cv2.polylines(
        frame,
        [np.array(points, dtype=np.int32)],
        True,
        (0, 255, 0),
        1
    )


# ==========================================
# HEAD POSE ESTIMATION
# ==========================================

def estimate_head_pose(landmarks, width, height):

    landmark_ids = [1, 152, 33, 263, 61, 291]
    image_points = []

    for index in landmark_ids:
        landmark = landmarks[index]

        image_points.append([
            landmark.x * width,
            landmark.y * height
        ])

    image_points = np.array(
        image_points,
        dtype=np.float64
    )

    model_points = np.array([
        [0.0, 0.0, 0.0],
        [0.0, -63.6, -12.5],
        [-43.3, 32.7, -26.0],
        [43.3, 32.7, -26.0],
        [-28.9, -28.9, -24.1],
        [28.9, -28.9, -24.1]
    ], dtype=np.float64)

    focal_length = width
    center = (width / 2.0, height / 2.0)

    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    distortion = np.zeros((4, 1), dtype=np.float64)

    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points,
        image_points,
        camera_matrix,
        distortion,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    angles = cv2.RQDecomp3x3(rotation_matrix)[0]

    pitch = float(angles[0])
    yaw = float(angles[1])
    roll = float(angles[2])

    return pitch, yaw, roll


# ==========================================
# MAIN WEBCAM FUNCTION
# ==========================================

def run_eye_detection():

    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        face_mesh.close()
        return

    attention_engine = AttentionEngine()
    tracker = SessionTracker()

    blink_count = 0
    eyes_closed = False
    closed_start = None

    print("FocusGuard AI - Attention Monitoring")
    print("Session tracking enabled.")
    print("Press Q to quit and save the session report.")

    try:

        while True:

            success, frame = camera.read()

            if not success:
                print("Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            results = face_mesh.process(rgb_frame)
            now = time.monotonic()

            # Default state for this frame
            attention_state = "Unknown"

            if results.multi_face_landmarks:

                face_landmarks = results.multi_face_landmarks[0]
                landmarks = face_landmarks.landmark

                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=(
                        mp_styles.get_default_face_mesh_contours_style()
                    )
                )

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

                # Count blinks when an eye closure ends
                if not eyes_open:

                    if not eyes_closed:
                        closed_start = now

                    eyes_closed = True

                else:

                    if eyes_closed and closed_start is not None:

                        duration = now - closed_start

                        if (
                            MIN_BLINK_SECONDS
                            <= duration
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

                    attention_state = attention_engine.update(
                        eyes_open=eyes_open,
                        pitch=pitch,
                        yaw=yaw,
                        now=now
                    )

                else:

                    pitch = yaw = roll = None

                    attention_state = attention_engine.update(
                        eyes_open=None,
                        pitch=None,
                        yaw=None,
                        now=now
                    )

                # State display color
                if attention_state == "Focused":
                    state_color = (0, 150, 0)

                elif attention_state == "Possibly Distracted":
                    state_color = (0, 165, 255)

                elif attention_state == "Prolonged Eye Closure":
                    state_color = (0, 0, 255)

                else:
                    state_color = (100, 100, 100)

                # Display eye measurements
                cv2.putText(
                    frame,
                    f"Left EAR: {left_ear:.3f}",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Right EAR: {right_ear:.3f}",
                    (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Blinks: {blink_count}",
                    (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2
                )

                # Display head pose
                if pose is not None:

                    cv2.putText(
                        frame,
                        f"Pitch: {pitch:.1f}",
                        (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 0, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Yaw: {yaw:.1f}",
                        (20, 150),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 0, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Roll: {roll:.1f}",
                        (20, 180),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 0, 0),
                        2
                    )

                cv2.putText(
                    frame,
                    f"Attention: {attention_state}",
                    (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    state_color,
                    2
                )

            else:

                # No face means the state is unknown
                attention_state = attention_engine.update(
                    eyes_open=None,
                    pitch=None,
                    yaw=None,
                    now=now
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
                    2
                )

            # ==========================================
            # SESSION TRACKING
            # ==========================================

            tracker.update(attention_state)
            summary = tracker.get_summary()

            duration = summary["duration_seconds"]
            minutes = int(duration // 60)
            seconds = int(duration % 60)

            cv2.putText(
                frame,
                f"Session: {minutes:02d}:{seconds:02d}",
                (20, 260),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )

            cv2.putText(
                frame,
                f"Focus: {summary['focus_percentage']:.1f}%",
                (20, 290),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )

            cv2.putText(
                frame,
                f"Distraction Events: {summary['distraction_events']}",
                (20, 320),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                2
            )

            cv2.putText(
                frame,
                f"Eye Closure Events: {summary['eye_closure_events']}",
                (20, 350),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                2
            )

            cv2.putText(
                frame,
                "FocusGuard AI | Press Q to quit",
                (20, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                2
            )

            cv2.imshow(
                "FocusGuard AI - Attention Monitoring",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        camera.release()
        face_mesh.close()
        cv2.destroyAllWindows()

        # Save the session report, even if the loop exits unexpectedly
        tracker.update(attention_engine.current_state)

        try:
            file_path = tracker.save_csv()
            summary = tracker.get_summary()

            print("\n========== SESSION SUMMARY ==========")
            print(f"Duration: {summary['duration_seconds']} seconds")
            print(f"Focus percentage: {summary['focus_percentage']}%")
            print(f"Focused time: {summary['focused_seconds']} seconds")
            print(
                "Possibly distracted time:",
                summary["distracted_seconds"],
                "seconds"
            )
            print(
                "Prolonged eye-closure time:",
                summary["eye_closure_seconds"],
                "seconds"
            )
            print("Distraction events:", summary["distraction_events"])
            print("Eye-closure events:", summary["eye_closure_events"])
            print("CSV report saved to:", file_path)
            print("=====================================")

        except OSError as error:
            print("Could not save session report:", error)

        print("FocusGuard AI stopped.")


if __name__ == "__main__":
    run_eye_detection()
