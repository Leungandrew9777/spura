# spura-engine/app/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.task_progress: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial progress if available
        if task_id in self.task_progress:
            await websocket.send_json(self.task_progress[task_id])
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        self.active_connections.remove(websocket)
    
    async def send_task_progress(self, task_id: str, progress: float, message: str):
        """Broadcast progress update to all connected clients"""
        self.task_progress[task_id] = {
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Broadcast to all connections watching this task
        for connection in self.active_connections:
            await connection.send_json(self.task_progress[task_id])
    
    def get_task_progress(self, task_id: str) -> dict:
        return self.task_progress.get(task_id, {})

manager = ConnectionManager()