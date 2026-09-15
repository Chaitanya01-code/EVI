from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.chat import chat_router
from app.database.connection import close_pool
from app.database.store import initialize_database_async
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
app.include_router(chat_router, prefix="/api")


@app.on_event("startup")
async def startup_database():
    try:
        await initialize_database_async()
    except Exception:
        logging.getLogger(__name__).exception("PostgreSQL initialization failed")
        raise


@app.on_event("shutdown")
async def shutdown_database():
    close_pool()

@app.get("/")
def read_root():
    return {"hello from evi"}