from pathlib import Path
import subprocess
import sys

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
BASE_DIR = Path(__file__).resolve().parent
VIDEO_DIR = BASE_DIR / "videos"


def find_videos():
    VIDEO_DIR.mkdir(exist_ok=True)
    return sorted(
        p for p in VIDEO_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )


def choose_video():
    videos = find_videos()
    print("\n=== Traffic Bet Arena ===")
    print(f"Video folder: {VIDEO_DIR}")

    if not videos:
        print("\nNo supported videos found in the videos folder.")
        print("Copy an .mp4, .avi, .mov, .mkv, .webm, or .m4v file there and run this again.")
        input("Press Enter to close...")
        raise SystemExit(1)

    print("\nAvailable videos:")
    for number, video in enumerate(videos, start=1):
        print(f"  {number}. {video.name}")

    while True:
        answer = input("\nEnter the video number or exact filename: ").strip()
        if answer.isdigit():
            index = int(answer) - 1
            if 0 <= index < len(videos):
                return videos[index]
            print("Invalid number.")
            continue

        selected = VIDEO_DIR / answer
        if selected.is_file() and selected.suffix.lower() in VIDEO_EXTENSIONS:
            return selected
        print("That video was not found in the videos folder.")


def main():
    video = choose_video()
    print(f"\nStarting with: {video.name}")
    print("Open http://localhost:8000 in your browser.")
    print("Press Ctrl+C to stop.\n")
    subprocess.run(
        [sys.executable, str(BASE_DIR / "app.py"), "--video", str(video)],
        cwd=BASE_DIR,
        check=False,
    )


if __name__ == "__main__":
    main()
