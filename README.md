# FocusGuard AI — Attention Monitoring & Analytics

FocusGuard AI is a computer-vision-based attention monitoring application built with Python, OpenCV, MediaPipe, Flask, HTML, CSS, and JavaScript. It analyzes visual signals such as eye landmarks and head pose to estimate attention states and present session analytics through a web dashboard.

> **Disclaimer:** FocusGuard AI provides experimental attention estimates, not a medical diagnosis or a definitive measurement of attention. Its output may be inaccurate in some lighting conditions, camera positions, and individual circumstances.

## Features

- **Face landmark detection:** Uses MediaPipe to identify facial landmarks.
- **Eye-blink tracking:** Calculates Eye Aspect Ratio (EAR) to support blink detection.
- **Head-pose estimation:** Uses OpenCV's `solvePnP()` to estimate pitch, yaw, and roll.
- **Attention-state classification:** Displays states such as Focused, Possibly Distracted, Prolonged Eye Closure, and Unknown.
- **Live webcam dashboard:** Streams the camera feed through a Flask application.
- **Real-time metrics:** Displays session duration, focus percentage, blink count, and distraction events.
- **Session tracking:** Tracks time spent in attention states and saves session summaries as CSV files.
- **Interactive charts:** Visualizes focus distribution, session focus comparisons, and distraction trends.
- **Historical analytics:** Calculates average focus, best session, total monitoring time, and saved-session counts.
- **Session filtering:** Supports analysis of recent sessions or all saved sessions.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Computer vision | OpenCV |
| Facial landmarks | MediaPipe |
| Backend | Flask |
| Frontend | HTML, CSS, JavaScript |
| Charts | Chart.js |
| Data storage | CSV files |
| Analytics | Python and JavaScript |

## Project Structure

```text
FocusGuard_AI/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── vision/
│   ├── __init__.py
│   ├── face_landmarks.py
│   └── session_tracker.py
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
└── data/
    └── sessions/
```

## Prerequisites

- Python version compatible with the dependencies in `requirements.txt`
- A webcam
- Git
- A modern web browser
- Internet access when loading Chart.js from its CDN

## Installation and Setup

### 1. Clone the repository

```bash
https://github.com/AmeyGhogare/FocusGuard_AI.git
cd FocusGuard_AI
```

### 2. Create a virtual environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

Open the local address shown in the Flask terminal. If the application uses Flask's default local configuration, it is usually:

```text
http://127.0.0.1:5000
```

### 5. Use the dashboard

1. Open the dashboard in your browser.
2. Click **Start Monitoring** and grant camera access if requested.
3. Observe the live attention state and session metrics.
4. Click **Stop Session** to end monitoring and save the session summary.
5. Review the saved sessions, historical KPI cards, and charts.

## How It Works

1. OpenCV captures frames from the webcam.
2. MediaPipe provides facial landmarks.
3. Eye Aspect Ratio calculations support blink and eye-closure detection.
4. OpenCV head-pose estimation calculates head orientation.
5. The attention engine classifies detected signals into application-defined states.
6. The session tracker accumulates state durations and event counts.
7. Flask exposes the live dashboard, webcam stream, and session-history endpoints.
8. Session summaries are saved as CSV files and used for historical analytics.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Renders the dashboard |
| `/api/start` | Starts monitoring |
| `/api/stop` | Stops monitoring and saves session data |
| `/api/stats` | Returns current session metrics |
| `/video_feed` | Streams webcam frames |
| `/api/history` | Returns saved session history |

## Data and Privacy

- Webcam monitoring requires access to a camera.
- Run the application locally for local development and testing.
- Generated session CSV files are excluded from Git by default.
- Do not commit personal session data, credentials, API keys, or environment files.
- Review any changes to data collection and storage before sharing or deploying the project.

## Limitations

- Lighting, camera placement, occlusion, and face-detection quality may affect results.
- Head pose and eye measurements are indirect visual signals and cannot establish a person's true mental state.
- Focus percentages depend on the application's classification logic and should not be treated as scientifically validated scores.
- Chart.js is loaded from a CDN, so the charts need network access unless the library is hosted locally.

## Future Improvements

- Add date-based session filtering and downloadable analytics reports.
- Add automated tests for attention classification and session tracking.
- Improve error handling for camera and browser-stream failures.
- Add configurable session thresholds and analytics settings.
- Evaluate performance across different lighting and camera conditions.


## Author

**Amey Ghogare**

GitHub: `https://github.com/AmeyGhogare`

