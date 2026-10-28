
import time
from vision.session_tracker import SessionTracker

tracker = SessionTracker()

print("Session started. Testing for a few seconds...")

tracker.update("Focused")
time.sleep(3)

tracker.update("Possibly Distracted")
time.sleep(2)

tracker.update("Focused")
time.sleep(2)

tracker.update("Prolonged Eye Closure")
time.sleep(2)

tracker.update("Focused")

print("\nSession Summary")
print("-----------------------------")

summary = tracker.get_summary()

for key, value in summary.items():
    print(key, ":", value)

file_path = tracker.save_csv()

print("\nCSV report saved to:", file_path)
