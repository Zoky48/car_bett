# Live Traffic Betting Simulation

## Windows: one-click setup and start

1. Put a traffic video file inside the `videos` folder. Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.m4v`.
2. Double-click **`setup_and_run.bat`**.
3. The script creates a Python virtual environment, installs `requirements.txt`, lists the videos, and asks which video to run.
4. Enter the displayed number or the exact filename.
5. Open **http://localhost:8000**.

You can also start it from Command Prompt:

```bat
setup_and_run.bat
```

## Manual start

```bat
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe start.py
```

## Project files

- `app.py` - FastAPI backend, OpenCV processing, game logic, WebSocket updates
- `index.html` - dark-themed single-page frontend
- `start.py` - selects a video from `videos/`
- `setup_and_run.bat` - Windows setup and launcher
- `videos/` - local traffic videos
- `requirements.txt` - Python dependencies
