from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

app = FastAPI()

# Store connected clients in a list
clients = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            # Keep the connection alive and listen for incoming messages if needed
            data = await websocket.receive_text()
            print(f"Received from client: {data}")
    except WebSocketDisconnect:
        clients.remove(websocket)
        print("Client disconnected")


# Function to broadcast logs to all connected WebSocket clients
async def broadcast_log(log_message: str):
    for client in clients:
        await client.send_text(log_message)
