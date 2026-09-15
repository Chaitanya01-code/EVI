import asyncio
import logging
import os
import threading

logger = logging.getLogger(__name__)
_engine_lock = threading.Lock()


def speak_text(text: str) -> bool:
	"""Speak EVI's response on the machine running the backend.

	TTS is optional so a missing audio driver or package never breaks chat.
	Set EVI_TTS_ENABLED=false to disable server-side speech.
	"""
	if not text or os.getenv("EVI_TTS_ENABLED", "true").lower() == "false":
		return False

	try:
		import pyttsx3

		with _engine_lock:
			engine = pyttsx3.init()
			engine.setProperty("rate", int(os.getenv("EVI_TTS_RATE", "175")))
			engine.say(text)
			engine.runAndWait()
			engine.stop()
		return True
	except Exception:
		logger.exception("EVI text-to-speech is unavailable")
		return False


async def speak_text_async(text: str) -> None:
	"""Run speech off the request path so Gemini/chat responses stay responsive."""
	loop = asyncio.get_running_loop()
	await loop.run_in_executor(None, speak_text, text)
