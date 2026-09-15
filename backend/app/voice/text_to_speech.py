import asyncio
import logging
import os
import threading
import base64
import tempfile

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


def synthesize_audio(text: str) -> str:
	"""Return WAV audio as a browser-playable data URL."""
	if not text or os.getenv("EVI_TTS_ENABLED", "true").lower() == "false":
		return ""

	output_path = None
	try:
		import pyttsx3

		with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output:
			output_path = output.name
		with _engine_lock:
			engine = pyttsx3.init()
			engine.setProperty("rate", int(os.getenv("EVI_TTS_RATE", "175")))
			engine.save_to_file(text, output_path)
			engine.runAndWait()
			engine.stop()
		with open(output_path, "rb") as audio_file:
			encoded_audio = base64.b64encode(audio_file.read()).decode("ascii")
		return f"data:audio/wav;base64,{encoded_audio}"
	except Exception:
		logger.exception("EVI audio synthesis is unavailable")
		raise
	finally:
		if output_path:
			try:
				os.remove(output_path)
			except OSError:
				logger.warning("Unable to remove temporary TTS file")


async def synthesize_audio_async(text: str) -> str:
	loop = asyncio.get_running_loop()
	return await loop.run_in_executor(None, synthesize_audio, text)
