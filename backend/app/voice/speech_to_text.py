import os
import json
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from uuid import uuid4

from app.core.context import WorkingContext
from app.router.intent_router import conversation_history, process_context

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

stt_router = APIRouter()

@stt_router.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session_id") or str(uuid4())

    if not DEEPGRAM_API_KEY:
        await websocket.send_json({"error": "Voice service is not configured. Add DEEPGRAM_API_KEY to the backend environment."})
        await websocket.close(code=1011)
        return
    
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
                            if is_final:
                                context = WorkingContext(
                                    session_id=session_id,
                                    transcript=transcript,
                                    input_type="voice",
                                    conversation_history=conversation_history(session_id),
                                )
                                result = await process_context(context)
                                await ws.send_json({
                                    "transcript": transcript,
                                    "is_final": True,
                                    "processing": result.model_dump(mode="json"),
                                })
                except Exception as e:
                    print(f"Error receiving from Deepgram: {e}")

            await asyncio.gather(
                sender(websocket, dg_socket),
                receiver(websocket, dg_socket)
            )
    except Exception as e:
        print(f"Deepgram connection error: {e}")
        try:
            await websocket.send_json({"error": "Could not connect to the transcription service."})
            await websocket.close(code=1011)
        except Exception:
            pass
