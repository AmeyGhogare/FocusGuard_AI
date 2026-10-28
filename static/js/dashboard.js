
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const videoFeed = document.getElementById("videoFeed");
const videoPlaceholder = document.getElementById("videoPlaceholder");

const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const cameraBadge = document.getElementById("cameraBadge");
const historyBody = document.getElementById("historyBody");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");

let monitoring = false;
let refreshInProgress = false;
let lastMessage = "";
let historyLoaded = false;

let focusChart = null;
let sessionFocusChart = null;
let distractionTrendChart = null;

const COLORS = {
    focused: "#37d6a2",
    distracted: "#ffad60",
    closure: "#ff6b81",
    unknown: "#8290a8",
    purple: "#8b7cff",
    blue: "#54a8ff",
    grid: "rgba(150, 163, 186, 0.13)",
    text: "#96a3ba"
};

function numberValue(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
}

function getValue(object, keys, fallback = 0) {
    for (const key of keys) {
        if (
            object &&
            object[key] !== undefined &&
            object[key] !== null &&
            object[key] !== ""
        ) {
            return object[key];
        }
    }

    return fallback;
}

function formatDuration(seconds) {
    const total = Math.max(0, Math.floor(numberValue(seconds)));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainingSeconds = total % 60;

    if (hours > 0) {
        return (
            String(hours).padStart(2, "0") + ":" +
            String(minutes).padStart(2, "0") + ":" +
            String(remainingSeconds).padStart(2, "0")
        );
    }

    return (
        String(minutes).padStart(2, "0") + ":" +
        String(remainingSeconds).padStart(2, "0")
    );
}

function formatPercentage(value) {
    return numberValue(value).toFixed(1) + "%";
}

function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function setProgressBar(id, percentage) {
    const element = document.getElementById(id);

    if (element) {
        const value = Math.max(0, Math.min(100, numberValue(percentage)));
        element.style.width = value + "%";
    }
}

function setCameraVisible(visible) {
    videoFeed.style.display = visible ? "block" : "none";
    videoPlaceholder.style.display = visible ? "none" : "block";

    if (!visible) {
        videoFeed.removeAttribute("src");
    }
}

function setMonitoringUI(active) {
    monitoring = active;

    startBtn.disabled = active;
    stopBtn.disabled = !active;

    statusText.textContent = active ? "Monitoring active" : "Ready to start";
    statusDot.classList.toggle("active", active);

    cameraBadge.textContent = active ? "Camera active" : "Camera offline";
    cameraBadge.classList.toggle("badge-active", active);
    cameraBadge.classList.toggle("badge-neutral", !active);
}

function updateAttentionState(state) {
    const normalized = String(state || "Unknown").toLowerCase();
    const indicator = document.getElementById("stateIndicator");

    setText("attentionState", state || "Unknown");

    indicator.classList.remove("focused", "distracted", "closure");

    if (normalized.includes("focus")) {
        indicator.classList.add("focused");
    } else if (normalized.includes("closure")) {
        indicator.classList.add("closure");
    } else if (normalized.includes("distract")) {
        indicator.classList.add("distracted");
    }
}

function updateDashboard(data) {
    const duration = numberValue(data.duration_seconds);
    const focus = numberValue(data.focus_percentage);

    const focused = numberValue(data.focused_seconds);
    const distracted = numberValue(data.distracted_seconds);
    const eyeClosure = numberValue(data.eye_closure_seconds);
    const unknown = numberValue(data.unknown_seconds);

    setText("duration", formatDuration(duration));
    setText("focusPercentage", formatPercentage(focus));
    setText("blinkCount", numberValue(data.blink_count));
    setText("distractionEvents", numberValue(data.distraction_events));
    setText("eyeClosureEvents", numberValue(data.eye_closure_events));

    setText("pitch", numberValue(data.pitch).toFixed(1) + "°");
    setText("yaw", numberValue(data.yaw).toFixed(1) + "°");

    updateAttentionState(data.state);

    setText("statusMessage", data.message || "Monitoring is ready.");

    // Calculate the percentages for the time breakdown.
    const total = focused + distracted + eyeClosure + unknown;

    let focusedPercent = 0;
    let distractedPercent = 0;
    let closurePercent = 0;
    let unknownPercent = 0;

    if (total > 0) {
        focusedPercent = (focused / total) * 100;
        distractedPercent = (distracted / total) * 100;
        closurePercent = (eyeClosure / total) * 100;
        unknownPercent = (unknown / total) * 100;
    }

    setText("focusedTime", formatPercentage(focusedPercent));
    setText("distractedTime", formatPercentage(distractedPercent));
    setText("eyeClosureTime", formatPercentage(closurePercent));
    setText("unknownTime", formatPercentage(unknownPercent));

    setProgressBar("focusedBar", focusedPercent);
    setProgressBar("distractedBar", distractedPercent);
    setProgressBar("eyeClosureBar", closurePercent);
    setProgressBar("unknownBar", unknownPercent);

    updateFocusChart(focused, distracted, eyeClosure, unknown);

    if (data.message && data.message !== lastMessage) {
        if (
            data.message.toLowerCase().includes("session saved") ||
            data.message.toLowerCase().includes("session stopped")
        ) {
            loadSessionHistory();
        }
    }

    lastMessage = data.message || "";
}

function createChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 250
        },
        plugins: {
            legend: {
                labels: {
                    color: COLORS.text,
                    usePointStyle: true,
                    pointStyle: "circle",
                    padding: 16,
                    font: {
                        size: 11
                    }
                }
            },
            tooltip: {
                backgroundColor: "#10182a",
                titleColor: "#edf2ff",
                bodyColor: "#edf2ff",
                borderColor: "#28354d",
                borderWidth: 1,
                padding: 10
            }
        }
    };
}

function initializeCharts() {
    if (typeof Chart === "undefined") {
        console.error(
            "Chart.js did not load. Check your internet connection or CDN access."
        );
        return;
    }

    const focusCanvas = document.getElementById("focusChart");
    const sessionCanvas = document.getElementById("sessionFocusChart");
    const trendCanvas = document.getElementById("distractionTrendChart");

    focusChart = new Chart(focusCanvas, {
        type: "doughnut",
        data: {
            labels: [
                "Focused",
                "Possibly Distracted",
                "Prolonged Eye Closure",
                "Unknown"
            ],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    COLORS.focused,
                    COLORS.distracted,
                    COLORS.closure,
                    COLORS.unknown
                ],
                borderColor: "#131b2e",
                borderWidth: 4,
                hoverOffset: 7
            }]
        },
        options: {
            ...createChartOptions(),
            cutout: "70%",
            plugins: {
                ...createChartOptions().plugins,
                legend: {
                    position: "bottom",
                    labels: createChartOptions().plugins.legend.labels
                }
            }
        }
    });

    sessionFocusChart = new Chart(sessionCanvas, {
        type: "bar",
        data: {
            labels: [],
            datasets: [{
                label: "Focus percentage",
                data: [],
                backgroundColor: COLORS.purple,
                hoverBackgroundColor: COLORS.blue,
                borderRadius: 6,
                maxBarThickness: 42
            }]
        },
        options: {
            ...createChartOptions(),
            scales: {
                x: {
                    ticks: {
                        color: COLORS.text,
                        maxRotation: 35,
                        minRotation: 0
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: COLORS.text,
                        callback: value => value + "%"
                    },
                    grid: {
                        color: COLORS.grid
                    }
                }
            },
            plugins: {
                ...createChartOptions().plugins,
                legend: {
                    display: false
                },
                tooltip: {
                    ...createChartOptions().plugins.tooltip,
                    callbacks: {
                        label: context => "Focus: " + context.parsed.y + "%"
                    }
                }
            }
        }
    });

    distractionTrendChart = new Chart(trendCanvas, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Distraction events",
                data: [],
                borderColor: COLORS.orange || "#ffad60",
                backgroundColor: "rgba(255, 173, 96, 0.12)",
                pointBackgroundColor: "#ffad60",
                pointBorderColor: "#131b2e",
                pointRadius: 4,
                pointHoverRadius: 6,
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            ...createChartOptions(),
            scales: {
                x: {
                    ticks: {
                        color: COLORS.text,
                        maxRotation: 35,
                        minRotation: 0
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: COLORS.text,
                        precision: 0
                    },
                    grid: {
                        color: COLORS.grid
                    }
                }
            },
            plugins: {
                ...createChartOptions().plugins,
                legend: {
                    display: false
                }
            }
        }
    });
}

function updateFocusChart(focused, distracted, eyeClosure, unknown) {
    if (!focusChart) {
        return;
    }

    focusChart.data.datasets[0].data = [
        Math.max(0, focused),
        Math.max(0, distracted),
        Math.max(0, eyeClosure),
        Math.max(0, unknown)
    ];

    focusChart.update("none");

    const total = focused + distracted + eyeClosure + unknown;

    setText(
        "focusChartNote",
        total > 0
            ? "Total classified time: " + formatDuration(total)
            : "Start a session to see your time distribution."
    );
}

function normalizeSession(session, index) {
    const duration = numberValue(
        getValue(session, ["duration_seconds", "duration", "total_duration"])
    );

    let focus = numberValue(
        getValue(session, ["focus_percentage", "focus_percent", "focus_pct"], -1)
    );

    if (focus < 0) {
        const focusedSeconds = numberValue(
            getValue(session, ["focused_seconds", "focused_duration"])
        );

        focus = duration > 0 ? (focusedSeconds / duration) * 100 : 0;
    }

    const sessionId = String(
        getValue(
            session,
            ["session_id", "session", "id"],
            "Session " + (index + 1)
        )
    );

    return {
        original: session,
        sessionId,
        duration,
        focus: Math.max(0, Math.min(100, focus)),
        distractions: numberValue(
            getValue(
                session,
                ["distraction_events", "distractions", "distraction_count"]
            )
        ),
        eyeClosures: numberValue(
            getValue(
                session,
                ["eye_closure_events", "eye_closures", "eye_closure_count"]
            )
        )
    };
}

function sessionLabel(session, index) {
    const id = session.sessionId || ("Session " + (index + 1));

    // Keep chart labels compact.
    if (id.length > 15) {
        return id.slice(-12);
    }

    return id;
}

function renderSessionHistory(sessions) {
    historyBody.replaceChildren();

    if (!sessions.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-cell";
        cell.textContent = "No saved sessions yet. Complete a session to see it here.";

        row.appendChild(cell);
        historyBody.appendChild(row);
        return;
    }

    sessions.forEach((session, index) => {
        const normalized = normalizeSession(session, index);
        const row = document.createElement("tr");

        const values = [
            normalized.sessionId,
            formatDuration(normalized.duration),
            formatPercentage(normalized.focus),
            normalized.distractions,
            normalized.eyeClosures
        ];

        values.forEach((value, cellIndex) => {
            const cell = document.createElement("td");

            if (cellIndex === 2) {
                const pill = document.createElement("span");
                pill.className = "focus-pill";
                pill.textContent = value;
                cell.appendChild(pill);
            } else {
                cell.textContent = String(value);
            }

            row.appendChild(cell);
        });

        historyBody.appendChild(row);
    });
}

function updateHistoryCharts(sessions) {
    if (!sessionFocusChart || !distractionTrendChart) {
        return;
    }

    // The API returns newest first. Reverse a copy for chronological charts.
    const chronological = sessions
        .map((session, index) => normalizeSession(session, index))
        .reverse();

    const labels = chronological.map(sessionLabel);
    const focusValues = chronological.map(session => session.focus);
    const distractionValues = chronological.map(
        session => session.distractions
    );

    sessionFocusChart.data.labels = labels;
    sessionFocusChart.data.datasets[0].data = focusValues;
    sessionFocusChart.update();

    distractionTrendChart.data.labels = labels;
    distractionTrendChart.data.datasets[0].data = distractionValues;
    distractionTrendChart.update();
}

async function refreshStats() {
    if (refreshInProgress) {
        return;
    }

    refreshInProgress = true;

    try {
        const response = await fetch("/api/stats", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Could not retrieve live statistics.");
        }

        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error("Stats refresh failed:", error);
        setText("statusMessage", "Unable to retrieve live statistics.");
    } finally {
        refreshInProgress = false;
    }
}

async function loadSessionHistory() {
    try {
        refreshHistoryBtn.disabled = true;

        const response = await fetch("/api/history", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Could not load session history.");
        }

        const data = await response.json();
        const sessions = Array.isArray(data.sessions) ? data.sessions : [];

        renderSessionHistory(sessions);
        updateHistoryCharts(sessions);
        historyLoaded = true;
    } catch (error) {
        console.error("Session history failed:", error);

        if (!historyLoaded) {
            historyBody.replaceChildren();

            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-cell";
            cell.textContent = "Unable to load session history. Try refreshing.";

            row.appendChild(cell);
            historyBody.appendChild(row);
        }
    } finally {
        refreshHistoryBtn.disabled = false;
    }
}

startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    setText("statusMessage", "Starting webcam monitoring...");

    try {
        const response = await fetch("/api/start", {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Could not start monitoring.");
        }

        setMonitoringUI(true);
        setCameraVisible(true);

        // A query parameter helps prevent a stale cached video stream.
        videoFeed.src = "/video_feed?t=" + Date.now();

        setText(
            "statusMessage",
            data.message || "Webcam monitoring started."
        );

        await refreshStats();
    } catch (error) {
        console.error("Start failed:", error);
        setText("statusMessage", error.message || "Unable to start monitoring.");
        setMonitoringUI(false);
        setCameraVisible(false);
    } finally {
        startBtn.disabled = monitoring;
    }
});

stopBtn.addEventListener("click", async () => {
    stopBtn.disabled = true;
    setText("statusMessage", "Stopping monitoring and saving session...");

    try {
        const response = await fetch("/api/stop", {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Could not stop monitoring.");
        }

        setMonitoringUI(false);
        setCameraVisible(false);

        setText(
            "statusMessage",
            data.message || "Session stopped. Refreshing saved sessions..."
        );

        await refreshStats();
        await loadSessionHistory();
    } catch (error) {
        console.error("Stop failed:", error);
        setText("statusMessage", error.message || "Unable to stop monitoring.");
    } finally {
        stopBtn.disabled = !monitoring;
    }
});

refreshHistoryBtn.addEventListener("click", loadSessionHistory);

initializeCharts();
setCameraVisible(false);
setMonitoringUI(false);

refreshStats();
loadSessionHistory();

setInterval(refreshStats, 1000);
