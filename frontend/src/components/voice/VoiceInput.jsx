import { useEffect, useRef, useState } from 'react';
import { sendCommand } from '../../services/api.js';

function pickFemaleVoice() {
  const synth = window.speechSynthesis;
  if (!synth) return null;

  const voices = synth.getVoices?.() || [];
  const femaleHints = [
    'female', 'zira', 'samantha', 'aria', 'hazel', 'susan', 'samantha', 'voice', 'google uk english female'
  ];

  const preferred = voices.find((voice) => {
    const name = `${voice.name} ${voice.lang} ${voice.voiceURI}`.toLowerCase();
    return femaleHints.some((hint) => name.includes(hint));
  });

  if (preferred) return preferred;

  const fallback = voices.find((voice) => voice.lang?.startsWith('en'));
  return fallback || null;
}

function VoiceInput({ context = 'Frontend mic capture for Nova voice route.', onResponse }) {
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const latestTranscript = useRef('');
  const recognitionRef = useRef(null);
  const continuousRef = useRef(false);

  const responseToSpeech = (result) => {
    const steps = result?.workflow?.execution?.steps || [];
    const unavailable = steps.find((step) =>
      step?.executed === false || step?.result?.error || String(step?.result?.message || '').startsWith('No real execution')
    );
    if (unavailable) {
      const detail = unavailable.result?.error || unavailable.result?.message || `the ${unavailable.tool || 'requested'} action`;
      return `I can't complete that request because I don't currently have permission or ability: ${detail}`;
    }
    if (result?.ok === false || result?.error) {
      return `I can't complete that request because ${result.error || 'the command was not permitted or available'}.`;
    }
    const workflow = result?.workflow?.return_context?.summary;
    const core = result?.nova?.return_context?.summary;
    return workflow || core || 'Command completed.';
  };

  const listen = () => {
    if (!continuousRef.current || recognitionRef.current) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      continuousRef.current = false;
      setError('Speech recognition is not available in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setListening(true);
      setError('');
    };

    recognition.onresult = (event) => {
      const nextTranscript = event.results[event.results.length - 1][0].transcript;
      latestTranscript.current = nextTranscript;
      setTranscript(nextTranscript);
    };

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') setError(`Speech capture error: ${event.error}`);
    };

    recognition.onend = async () => {
      recognitionRef.current = null;
      setListening(false);
      const cleanedTranscript = latestTranscript.current.trim();
      latestTranscript.current = '';
      if (!continuousRef.current) return;

      if (!cleanedTranscript) {
        listen();
        return;
      }

      try {
        const result = await sendCommand(cleanedTranscript, context);
        setResponse(result);
        onResponse?.(result);

        if ('speechSynthesis' in window) {
          setSpeaking(true);
          const utterance = new SpeechSynthesisUtterance(responseToSpeech(result));
          const selectedVoice = pickFemaleVoice();
          if (selectedVoice) {
            utterance.voice = selectedVoice;
          }
          utterance.volume = 1;
          utterance.rate = 1.0;
          utterance.pitch = 1.12;
          utterance.onend = () => {
            setSpeaking(false);
            if (continuousRef.current) listen();
          };
          utterance.onerror = () => {
            setSpeaking(false);
            if (continuousRef.current) listen();
          };
          window.speechSynthesis.speak(utterance);
        } else {
          listen();
        }
      } catch (sendError) {
        setError(sendError.message);
        if (continuousRef.current) listen();
      }
    };

    recognition.start();
  };

  const toggleRecognition = () => {
    if (continuousRef.current) {
      continuousRef.current = false;
      recognitionRef.current?.abort();
      recognitionRef.current = null;
      window.speechSynthesis?.cancel();
      setListening(false);
      setSpeaking(false);
      return;
    }
    continuousRef.current = true;
    listen();
  };

  useEffect(() => () => {
    continuousRef.current = false;
    recognitionRef.current?.abort();
    window.speechSynthesis?.cancel();
  }, []);

  return (
    <section className="voice-input-panel">
      <button className="mic-button" onClick={toggleRecognition} aria-pressed={continuousRef.current}>
        {continuousRef.current ? (speaking ? 'Speaking… Stop mic' : listening ? 'Listening… Stop mic' : 'Voice loop active — Stop mic') : '🎙️ Start voice loop'}
      </button>

      <div className="voice-transcript">
        <span>Transcript:</span>
        <strong>{transcript || 'No transcript yet'}</strong>
      </div>

      {error && <div className="voice-error">{error}</div>}

      {response && (
        <pre className="voice-response">
          {JSON.stringify(response, null, 2)}
        </pre>
      )}
    </section>
  );
}

export default VoiceInput;
