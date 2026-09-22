import asyncio
import base64
import os
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

MARKET_OPTIONS = [
    {"id": "under_30", "label": "Under 30", "odds": 2.25},
    {"id": "thirty_to_thirty_seven", "label": "30-37", "odds": 2.85},
    {"id": "over_38", "label": "Over 38", "odds": 3.5},
]


class TrafficAnalyzer:
    def __init__(self, source: Any = 0, line_percent: float = 0.68):
        self.source = source
        self.line_percent = line_percent
        self.cap = None
        self.simulated = False
        self.latest_frame = None
        self.latest_frame_b64 = ""
        self.crossed_count = 0
        self.line_x = 0
        self.tracked_objects: Dict[int, Dict[str, Any]] = {}
        self.next_object_id = 1
        self.simulation_cars: List[Dict[str, float]] = []
        self._init_video_source()

    def _init_video_source(self) -> None:
        if self.source in (None, "", "0"):
            self.source = 0
        try:
            self.cap = cv2.VideoCapture(int(self.source) if str(self.source).isdigit() else str(self.source))
            if not self.cap.isOpened():
                self.cap = None
                self.simulated = True
        except Exception:
            self.cap = None
            self.simulated = True

        if self.simulated:
            self._seed_simulated_cars()

    def _seed_simulated_cars(self) -> None:
        self.simulation_cars = []
        for i in range(8):
            self.simulation_cars.append(
                {
                    "x": float(np.random.randint(20, 700)),
                    "y": float(np.random.randint(120, 340)),
                    "w": float(np.random.randint(24, 46)),
                    "h": float(np.random.randint(18, 28)),
                    "speed": float(np.random.uniform(1.5, 4.0)),
                    "direction": 1 if i % 2 == 0 else -1,
                    "crossed": False,
                }
            )

    def _next_simulated_frame(self) -> np.ndarray:
        width, height = 960, 540
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (width, height), (15, 18, 22), -1)
        cv2.rectangle(frame, (0, 90), (width, 450), (35, 38, 42), -1)
        cv2.line(frame, (0, 120), (width, 120), (55, 55, 55), 2)
        cv2.line(frame, (0, 420), (width, 420), (55, 55, 55), 2)
        self.line_x = int(width * self.line_percent)
        cv2.line(frame, (self.line_x, 0), (self.line_x, height), (0, 255, 255), 3)

        for car in self.simulation_cars:
            x = int(car["x"])
            y = int(car["y"])
            w = int(car["w"])
            h = int(car["h"])
            color = (48, 196, 255) if car["direction"] > 0 else (255, 140, 55)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 1)

            new_x = car["x"] + car["speed"] * car["direction"]
            if new_x < -60:
                new_x = width + 20
                car["crossed"] = False
            if new_x > width + 60:
                new_x = -20
                car["crossed"] = False
            car["x"] = new_x

            if not car["crossed"] and car["direction"] > 0 and x <= self.line_x <= new_x:
                self.crossed_count += 1
                car["crossed"] = True
            if not car["crossed"] and car["direction"] < 0 and x >= self.line_x >= new_x:
                self.crossed_count += 1
                car["crossed"] = True

        return frame

    def _process_video_frame(self, frame: np.ndarray) -> np.ndarray:
        if frame is None:
            return None

        height, width = frame.shape[:2]
        self.line_x = int(width * self.line_percent)
        cv2.line(frame, (self.line_x, 0), (self.line_x, height), (0, 255, 255), 3)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        new_tracks: Dict[int, Dict[str, Any]] = {}
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 800:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + w // 2
            cy = y + h // 2

            closest_id = None
            closest_distance = float("inf")
            for obj_id, previous in self.tracked_objects.items():
                dist = abs(previous["cx"] - cx) + abs(previous["cy"] - cy)
                if dist < closest_distance:
                    closest_distance = dist
                    closest_id = obj_id

            if closest_id is None:
                obj_id = self.next_object_id
                self.next_object_id += 1
            else:
                obj_id = closest_id

            previous = self.tracked_objects.get(obj_id, {})
            previous_x = previous.get("cx")
            previous_y = previous.get("cy")
            crossed = previous.get("crossed", False)
            if not crossed:
                if previous_x is not None and previous_x <= self.line_x <= cx:
                    self.crossed_count += 1
                    crossed = True
                elif previous_x is not None and previous_x >= self.line_x >= cx:
                    self.crossed_count += 1
                    crossed = True

            new_tracks[obj_id] = {"cx": cx, "cy": cy, "crossed": crossed}
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"#{obj_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        self.tracked_objects = new_tracks
        return frame

    def next_frame(self) -> Optional[np.ndarray]:
        if self.simulated:
            frame = self._next_simulated_frame()
        else:
            if self.cap is None:
                return None
            ok, frame = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            if not ok:
                return None
            frame = self._process_video_frame(frame)

        if frame is None:
            return None

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        self.latest_frame = frame
        self.latest_frame_b64 = base64.b64encode(buffer.tobytes()).decode("ascii")
        return frame


class GameManager:
    def __init__(self, video_source: Any = 0):
        self.traffic = TrafficAnalyzer(video_source)
        self.phase = "betting_open"
        self.round_number = 1
        self.prebet_duration = 8.0
        self.count_duration = 30.0
        self.timer_remaining = self.prebet_duration
        self.crossed_vehicles = 0
        self.player_bet: Optional[Dict[str, Any]] = None
        self.result: Optional[Dict[str, Any]] = None
        self.status_text = "Betting Open"
        self.websockets: List[WebSocket] = []

    def get_market_by_id(self, market_id: str) -> Optional[Dict[str, Any]]:
        for option in MARKET_OPTIONS:
            if option["id"] == market_id:
                return option
        return None

    def _winning_market(self) -> str:
        count = self.crossed_vehicles
        if count < 30:
            return "under_30"
        if 30 <= count <= 37:
            return "thirty_to_thirty_seven"
        return "over_38"

    def place_bet(self, market_id: str, amount: float) -> Dict[str, Any]:
        if self.phase != "betting_open":
            raise HTTPException(status_code=400, detail="Betting is closed for this round.")
        market = self.get_market_by_id(market_id)
        if market is None:
            raise HTTPException(status_code=400, detail="Unknown betting market.")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Bet amount must be positive.")

        self.player_bet = {"market_id": market["id"], "amount": float(amount), "odds": float(market["odds"])}
        return {"ok": True, "bet": self.player_bet}

    def settle_round(self) -> None:
        winner = self._winning_market()
        if self.player_bet is None:
            self.result = {
                "winner": winner,
                "your_payout": 0.0,
                "message": "No bet placed.",
            }
            return

        market = self.get_market_by_id(self.player_bet["market_id"])
        if market is None:
            self.result = {"winner": winner, "your_payout": 0.0, "message": "Invalid bet settlement."}
            return

        if self.player_bet["market_id"] == winner:
            payout = self.player_bet["amount"] * market["odds"]
            message = f"Win! {market['label']} landed."
        else:
            payout = 0.0
            message = f"Loss. {label_for_market(winner)} was the winner."

        self.result = {
            "winner": winner,
            "your_payout": payout,
            "message": message,
            "bet": self.player_bet,
        }

    async def broadcast_state(self) -> None:
        payload = {
            "type": "state",
            "data": {
                "phase": self.phase,
                "round_number": self.round_number,
                "timer": round(self.timer_remaining, 1),
                "market_options": MARKET_OPTIONS,
                "crossed_vehicles": self.crossed_vehicles,
                "status_text": self.status_text,
                "player_bet": self.player_bet,
                "result": self.result,
                "frame": self.traffic.latest_frame_b64,
            },
        }
        for ws in list(self.websockets):
            try:
                await ws.send_json(payload)
            except Exception:
                self.websockets.remove(ws)

    async def next_tick(self) -> None:
        frame = self.traffic.next_frame()
        if frame is not None:
            self.crossed_vehicles = self.traffic.crossed_count

        if self.phase == "betting_open":
            self.timer_remaining -= 0.2
            self.status_text = f"Betting Open - {max(0, self.timer_remaining):.0f}s"
            if self.timer_remaining <= 0:
                self.phase = "counting"
                self.timer_remaining = self.count_duration
                self.status_text = "Counting..."
                self.traffic.crossed_count = 0
                self.crossed_vehicles = 0
                if self.player_bet is not None:
                    self.player_bet = self.player_bet

        elif self.phase == "counting":
            self.timer_remaining -= 0.2
            self.crossed_vehicles = self.traffic.crossed_count
            self.status_text = "Counting..."
            if self.timer_remaining <= 0:
                self.phase = "settled"
                self.timer_remaining = 0.0
                self.status_text = "Round Settled"
                self.settle_round()

        elif self.phase == "settled":
            self.status_text = "Round Settled"
            await asyncio.sleep(4.0)
            self.round_number += 1
            self.phase = "betting_open"
            self.timer_remaining = self.prebet_duration
            self.traffic.crossed_count = 0
            self.crossed_vehicles = 0
            self.player_bet = None
            self.result = None
            self.status_text = "Betting Open"

        await self.broadcast_state()

    async def run(self) -> None:
        while True:
            await self.next_tick()
            await asyncio.sleep(0.2)


def label_for_market(market_id: str) -> str:
    market_map = {option["id"]: option["label"] for option in MARKET_OPTIONS}
    return market_map.get(market_id, "Unknown")


def create_app(video_source: Any = 0) -> FastAPI:
    app = FastAPI(title="Live Traffic Betting Mirage")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    manager = GameManager(video_source)
    app.state.game_manager = manager

    @app.get("/")
    async def index():
        return FileResponse("index.html")

    @app.get("/api/state")
    async def api_state() -> Dict[str, Any]:
        return {
            "phase": manager.phase,
            "round_number": manager.round_number,
            "timer": round(manager.timer_remaining, 1),
            "market_options": MARKET_OPTIONS,
            "crossed_vehicles": manager.crossed_vehicles,
            "status_text": manager.status_text,
            "player_bet": manager.player_bet,
            "result": manager.result,
            "frame": manager.traffic.latest_frame_b64,
        }

    @app.post("/api/place_bet")
    async def place_bet(payload: Dict[str, Any]) -> Dict[str, Any]:
        market_id = payload.get("option_id") or payload.get("market_id")
        amount = payload.get("amount")
        if market_id is None or amount is None:
            raise HTTPException(status_code=400, detail="Missing 'option_id' or 'amount'.")
        return manager.place_bet(str(market_id), float(amount))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        manager.websockets.append(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            if websocket in manager.websockets:
                manager.websockets.remove(websocket)

    @app.on_event("startup")
    async def startup_event() -> None:
        asyncio.create_task(manager.run())

    return app


app = create_app(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Live traffic betting simulator")
    parser.add_argument("--video", default="0", help="Path to a video file or webcam index; default uses webcam 0")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port for the API")
    args = parser.parse_args()
    app = create_app(args.video if args.video not in (None, "", "0") else 0)
    uvicorn.run(app, host=args.host, port=args.port)
