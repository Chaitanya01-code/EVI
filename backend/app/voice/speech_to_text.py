import websockets
import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv


load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

text_to_speech = APIRouter()

@text_to_speech.websocket("/listen")
async def listen(websocket: websocket.websocket):
    await websocket.accept()

    deepgram_url = f"wss://api.deepgram.com/v1/listen?access_token={DEEPGRAM_API_KEY}"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
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
