
import time


class AttentionEngine:
    def __init__(
        self,
        eye_closed_threshold=1.5,
        look_away_threshold=2.0,
        max_yaw=25.0,
        max_pitch=20.0
    ):
        self.eye_closed_threshold = eye_closed_threshold
        self.look_away_threshold = look_away_threshold
        self.max_yaw = max_yaw
        self.max_pitch = max_pitch

        self.eye_closed_start = None
        self.look_away_start = None

        self.current_state = "Focused"
        self.state_start = time.monotonic()

    def update(self, eyes_open, pitch, yaw, current_time=None):
        if current_time is None:
            current_time = time.monotonic()

        # Missing face or invalid measurements should not be
        # interpreted as proof of distraction.
        if pitch is None or yaw is None or eyes_open is None:
            self.eye_closed_start = None
            self.look_away_start = None
            return "Unknown"

        # Track prolonged eye closure
        if not eyes_open:
            if self.eye_closed_start is None:
                self.eye_closed_start = current_time
        else:
            self.eye_closed_start = None

        # Track sustained head turn
        looking_away = (
            abs(yaw) > self.max_yaw
            or abs(pitch) > self.max_pitch
        )

        if looking_away:
            if self.look_away_start is None:
                self.look_away_start = current_time
        else:
            self.look_away_start = None

        # Prioritize prolonged eye closure
        if (
            self.eye_closed_start is not None
            and current_time - self.eye_closed_start
            >= self.eye_closed_threshold
        ):
            new_state = "Prolonged Eye Closure"

        elif (
            self.look_away_start is not None
            and current_time - self.look_away_start
            >= self.look_away_threshold
        ):
            new_state = "Possibly Distracted"

        else:
            new_state = "Focused"

        if new_state != self.current_state:
            self.current_state = new_state
            self.state_start = current_time

        return self.current_state
