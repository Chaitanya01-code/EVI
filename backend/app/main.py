from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.voice.speech_to_text import stt_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt_router, prefix="/api/voice")

@app.get("/")
def read_root():
    return {"hello from evi"}