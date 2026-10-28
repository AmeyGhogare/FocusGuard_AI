
import csv
import os
import time
from datetime import datetime


class SessionTracker:

    def __init__(self):
        self.start_time = time.time()
        self.last_update = self.start_time

        self.current_state = "Unknown"
        self.state_durations = {
            "Focused": 0.0,
            "Possibly Distracted": 0.0,
            "Prolonged Eye Closure": 0.0,
            "Unknown": 0.0
        }

        self.distraction_events = 0
        self.eye_closure_events = 0

        self.session_id = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

    def update(self, state, now=None):
        if now is None:
            now = time.time()

        elapsed = now - self.last_update

        if elapsed < 0:
            elapsed = 0

        # Add elapsed time to the previous state
        if self.current_state in self.state_durations:
            self.state_durations[self.current_state] += elapsed

        # Count an event only when entering a state
        if state != self.current_state:
            if state == "Possibly Distracted":
                self.distraction_events += 1

            elif state == "Prolonged Eye Closure":
                self.eye_closure_events += 1

        self.current_state = state
        self.last_update = now

    def get_summary(self):
        now = time.time()

        # Include time spent in the current state
        durations = self.state_durations.copy()

        elapsed = now - self.last_update
        if elapsed < 0:
            elapsed = 0

        if self.current_state in durations:
            durations[self.current_state] += elapsed

        total_duration = now - self.start_time

        known_duration = (
            durations["Focused"]
            + durations["Possibly Distracted"]
            + durations["Prolonged Eye Closure"]
        )

        if known_duration > 0:
            focus_percentage = (
                durations["Focused"] / known_duration
            ) * 100
        else:
            focus_percentage = 0.0

        return {
            "session_id": self.session_id,
            "duration_seconds": round(total_duration, 2),
            "focused_seconds": round(durations["Focused"], 2),
            "distracted_seconds": round(
                durations["Possibly Distracted"], 2
            ),
            "eye_closure_seconds": round(
                durations["Prolonged Eye Closure"], 2
            ),
            "unknown_seconds": round(durations["Unknown"], 2),
            "focus_percentage": round(focus_percentage, 2),
            "distraction_events": self.distraction_events,
            "eye_closure_events": self.eye_closure_events
        }

    def save_csv(self, folder="data/sessions"):
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(
            folder,
            "session_" + self.session_id + ".csv"
        )

        summary = self.get_summary()

        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=summary.keys()
            )

            writer.writeheader()
            writer.writerow(summary)

        return file_path
