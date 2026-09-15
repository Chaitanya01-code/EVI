import os
import json
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

stt_router = APIRouter()

@stt_router.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # You might want to adjust parameters like encoding, sample_rate based on frontend
    deepgram_url = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}"
    }

    try:
        async with websockets.connect(deepgram_url, extra_headers=headers) as dg_socket:
            
            async def sender(ws: WebSocket, dg):
                try:
                    while True:
                        data = await ws.receive_bytes()
                        await dg.send(data)
                except WebSocketDisconnect:
                    print("Client disconnected")
                except Exception as e:
                    print(f"Error sending to Deepgram: {e}")
                    
            async def receiver(ws: WebSocket, dg):
                try:
                    async for message in dg:
                        msg = json.loads(message)
                        is_final = msg.get("is_final", False)
                        transcript = msg.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        
                        if transcript:
                            await ws.send_json({
                                "transcript": transcript,
                                "is_final": is_final
                            })
                except Exception as e:
                    print(f"Error receiving from Deepgram: {e}")

            await asyncio.gather(
                sender(websocket, dg_socket),
                receiver(websocket, dg_socket)
            )
    except Exception as e:
        print(f"Deepgram connection error: {e}")
        await websocket.close()
