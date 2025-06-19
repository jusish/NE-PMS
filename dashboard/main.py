# dashboard/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
from pathlib import Path
import os

# Add parent directory to path to import modules
import sys

from starlette.responses import PlainTextResponse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.database_utils import DatabaseManager

app = FastAPI(title="Parking Management Dashboard", version="1.0.0")

# Setup templates and static files
templates = Jinja2Templates(directory="/home/hrh/Documents/Workspace/PMS/dashboard/templates")
LOG_FILE_PATH = "/home/hrh/Documents/Workspace/PMS/logs/parking_20250602.log"
app.mount("/static", StaticFiles(directory="/home/hrh/Documents/Workspace/PMS/dashboard/static"), name="static")

# Initialize database
db = DatabaseManager()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    with db.get_connection() as conn:
        # Total vehicles today
        today = datetime.now().strftime('%Y-%m-%d')
        total_today = conn.execute(
            "SELECT COUNT(*) FROM parking_records WHERE DATE(entry_time) = ?",
            (today,)
        ).fetchone()[0]

        # Currently parked (unpaid records)
        currently_parked = conn.execute(
            "SELECT COUNT(*) FROM parking_records WHERE payment_status = 0"
        ).fetchone()[0]

        # Total revenue today
        revenue_today = conn.execute(
            "SELECT COALESCE(SUM(due_payment), 0) FROM parking_records WHERE DATE(entry_time) = ? AND payment_status = 1",
            (today,)
        ).fetchone()[0]

        # Average parking duration (in minutes)
        avg_duration = conn.execute(
            """SELECT AVG(
                CASE 
                    WHEN exit_time IS NOT NULL 
                    THEN (julianday(exit_time) - julianday(entry_time)) * 24 * 60 
                    ELSE NULL 
                END
            ) FROM parking_records WHERE DATE(entry_time) = ?""",
            (today,)
        ).fetchone()[0] or 0

    return {
        "total_today": total_today,
        "currently_parked": currently_parked,
        "revenue_today": float(revenue_today),
        "avg_duration": round(avg_duration, 1)
    }


@app.get("/api/recent-activities")
async def get_recent_activities():
    """Get recent parking activities"""
    with db.get_connection() as conn:
        activities = conn.execute(
            """SELECT car_plate, entry_time, exit_time, due_payment, payment_status
               FROM parking_records 
               ORDER BY entry_time DESC 
               LIMIT 10"""
        ).fetchall()

    return [dict(activity) for activity in activities]


@app.get("/api/hourly-data")
async def get_hourly_data():
    """Get hourly parking data for charts"""
    today = datetime.now().strftime('%Y-%m-%d')

    with db.get_connection() as conn:
        hourly_data = conn.execute(
            """SELECT 
                strftime('%H', entry_time) as hour,
                COUNT(*) as entries,
                COALESCE(SUM(CASE WHEN payment_status = 1 THEN due_payment ELSE 0 END), 0) as revenue
               FROM parking_records 
               WHERE DATE(entry_time) = ?
               GROUP BY strftime('%H', entry_time)
               ORDER BY hour""",
            (today,)
        ).fetchall()

    # Fill missing hours with zeros
    hours_data = {str(i).zfill(2): {"entries": 0, "revenue": 0} for i in range(24)}

    for row in hourly_data:
        hours_data[row['hour']] = {
            "entries": row['entries'],
            "revenue": float(row['revenue'])
        }

    return hours_data


@app.get("/api/parking-records")
async def get_parking_records(page: int = 1, limit: int = 20):
    """Get paginated parking records"""
    offset = (page - 1) * limit

    with db.get_connection() as conn:
        records = conn.execute(
            """SELECT * FROM parking_records 
               ORDER BY entry_time DESC 
               LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()

        total = conn.execute("SELECT COUNT(*) FROM parking_records").fetchone()[0]

    return {
        "records": [dict(record) for record in records],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@app.get("/api/search")
async def search_records(plate: str = None, date: str = None):
    """Search parking records"""
    query = "SELECT * FROM parking_records WHERE 1=1"
    params = []

    if plate:
        query += " AND car_plate LIKE ?"
        params.append(f"%{plate}%")

    if date:
        query += " AND DATE(entry_time) = ?"
        params.append(date)

    query += " ORDER BY entry_time DESC LIMIT 50"

    with db.get_connection() as conn:
        records = conn.execute(query, params).fetchall()

    return [dict(record) for record in records]


@app.get("/api/logs", response_class=PlainTextResponse)
async def read_logs(lines: int = 100):
    """
    Read the last `lines` lines from the logs.log file.
    """
    if not Path(LOG_FILE_PATH).exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        with open(LOG_FILE_PATH, "r") as file:
            log_lines = file.readlines()
            return "".join(log_lines[-lines:])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates
            stats = await get_dashboard_stats()
            await manager.send_personal_message(
                json.dumps({"type": "stats_update", "data": stats}),
                websocket
            )
            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Utility function to broadcast updates (call this from your main modules)
async def broadcast_update(event_type: str, data: Dict[Any, Any]):
    """Broadcast updates to all connected clients"""
    message = json.dumps({"type": event_type, "data": data})
    await manager.broadcast(message)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)