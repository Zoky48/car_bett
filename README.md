# Live Traffic Betting Simulation

This project is a dark-mode, live traffic betting game demo built with Python + FastAPI and a web frontend.

Features included:
- live traffic feed from webcam or a sample MP4 file
- vehicle crossing detection with OpenCV-based contour tracking
- virtual crossing line overlay
- 30-second round timer and betting options
- win/loss settlement logic
- real-time dashboard using WebSockets

## Requirements

Install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Start the app

Run with a sample MP4 file:

```bash
python app.py --video ./sample_traffic.mp4
```

Or use your webcam:

```bash
python app.py --video 0
```

Then open:

```text
http://localhost:8000
```

## Files

- `app.py` - backend, game logic, traffic counting, WebSocket server
- `index.html` - single-page frontend UI
- `requirements.txt` - Python dependencies

## Notes

- If no video file or webcam is available, the app automatically switches to a simulated traffic animation so the game still runs.
- Update the betting options in `MARKET_OPTIONS` inside `app.py` to modify odds and labels.
- The line placement follows a percentage of the frame width (`line_percent` in `TrafficAnalyzer`).

## Dependencies

```text
fastapi
uvicorn
opencv-python
numpy
python-socketio
```

Optional for YOLO-based advanced detection:

```text
ultralytics
```
