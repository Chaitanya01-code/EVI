from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.voice.speech_to_text import text_to_speech


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(text_to_speech, prefix="/api/voice")

@app.get("/")
def read_root():
    return {"hello from evi"}