import { useEffect, useRef, useState } from 'react';
import './App.css';
import { connectLabEvents, getObservability, submitChat } from './services/labApi';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function toPcm16(input, inputSampleRate) {
  const sampleRateRatio = inputSampleRate / 16000;
  const outputLength = Math.max(1, Math.round(input.length / sampleRateRatio));
  const output = new ArrayBuffer(outputLength * 2);
  const view = new DataView(output);

  for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
    const inputIndex = Math.min(input.length - 1, Math.floor(outputIndex * sampleRateRatio));
    const sample = Math.max(-1, Math.min(1, input[inputIndex]));
    view.setInt16(outputIndex * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return output;
}

const MicIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
    <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.92V20H9a1 1 0 0 0 0 2h6a1 1 0 0 0 0-2h-2v-2.08A7 7 0 0 0 19 11z"/>
  </svg>
);

const FlaskIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 2v7.31L4.62 18.2A2 2 0 0 0 6.34 21h11.32a2 2 0 0 0 1.72-2.8L14 9.31V2" />
    <path d="M8.5 2h7" />
    <path d="M7 16h10" />
  </svg>
);

const LAB_TABS = [
  ['overview', 'Overview'], ['tasks', 'Tasks'], ['agents', 'Agents'], ['activity', 'Activity'],
  ['traces', 'Traces'], ['work', 'Work Context'], ['applications', 'Applications'],
  ['desktop', 'Desktop Control'], ['tools', 'Tools'], ['inquiry', 'Inquiry'],
  ['research', 'Research'], ['memory', 'Memory'], ['decisions', 'Decisions'],
  ['projects', 'Projects'], ['verification', 'Verification'], ['errors', 'Errors'],
  ['performance', 'Performance'], ['models', 'Models'], ['security', 'Security'],
  ['integrations', 'Integrations'], ['settings', 'Settings'],
];

function displayValue(value) {
  if (value === null || value === undefined || value === '') return 'Not available';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function LabRows({ items, empty = 'No data' }) {
  if (!items?.length) return <div className="lab-task-item">{empty}</div>;
  return <div className="lab-tasks-list">{items.map((item, index) => (
    <div className="lab-task-item lab-detail-item" key={item.id || item.task_id || item.question_id || `${index}-${JSON.stringify(item).slice(0, 20)}`}>
      {Object.entries(item).slice(0, 8).map(([key, value]) => (
        <span key={key}><strong>{key.replaceAll('_', ' ')}</strong>: {displayValue(value)}</span>
      ))}
    </div>
  ))}</div>;
}

function LabExtendedPanel({ tab, data, activityEvents }) {
  const unavailable = data?.[tab]?.status === 'not_available';
  const title = LAB_TABS.find(([id]) => id === tab)?.[1] || 'EVI Lab';
  if (unavailable) return <div className="lab-card"><div className="lab-card-header"><h3>{title}</h3><span className="lab-tag">Unavailable</span></div><p className="lab-desc">{data[tab].message}</p></div>;

  const panels = {
    tasks: data?.tasks,
    activity: activityEvents,
    traces: data?.traces,
    work: data?.work_context ? [data.work_context] : [],
    applications: data?.applications,
    desktop: [data?.desktop],
    tools: data?.tools,
    inquiry: data?.inquiry?.all,
    research: data?.research?.results,
    memory: data?.memory?.data,
    decisions: data?.decisions,
    projects: data?.projects?.data,
    verification: data?.verification,
    errors: data?.errors,
    performance: data?.performance ? [data.performance] : [],
    models: data?.models ? [data.models] : [],
    security: data?.security ? [data.security] : [],
    integrations: Object.entries(data?.integrations || {}).map(([name, status]) => ({ name, status })),
    settings: [{ status: 'No Lab-specific settings configured' }],
  };
  return <div className="lab-card">
    <div className="lab-card-header"><h3>{title}</h3><span className="lab-tag green">Live</span></div>
    <p className="lab-desc">Operational information from the current EVI runtime.</p>
    <LabRows items={panels[tab]} />
  </div>;
}

function App() {
  const [listening, setListening] = useState(false);
  const [pulseAnim, setPulseAnim] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('Connecting to EVI...');
  const [error, setError] = useState('');
  const [assistantResponse, setAssistantResponse] = useState('');
  const [executionEvents, setExecutionEvents] = useState([]);
  const [labData, setLabData] = useState(null);
  const [labError, setLabError] = useState('');
  const [textInput, setTextInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const [backgroundEnabled, setBackgroundEnabled] = useState(true);
  const [labOpen, setLabOpen] = useState(false);
  const [labTab, setLabTab] = useState('overview');
  const [activityEvents, setActivityEvents] = useState([]);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [userId] = useState(() => {
    const storedUserId = window.localStorage.getItem('evi-user-id');
    if (storedUserId) return storedUserId;
    const newUserId = crypto.randomUUID();
    window.localStorage.setItem('evi-user-id', newUserId);
    return newUserId;
  });
  const audioRef = useRef(null);
  const socketRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioSourceRef = useRef(null);
  const processorRef = useRef(null);

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE_URL}/`)
      .then(response => {
        if (!response.ok) throw new Error('Backend returned an error');
        return response.json();
      })
      .then(() => {
        if (active) setConnectionStatus('Ready');
      })
      .catch(() => {
        if (active) setConnectionStatus('Backend unavailable');
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => () => stopListening(), []);

  useEffect(() => {
    if (!labOpen) return undefined;
    let active = true;
    setLabError('');
    getObservability()
      .then(snapshot => {
        if (active) {
          setLabData(snapshot);
          setActivityEvents(snapshot.events || []);
        }
      })
      .catch(() => {
        if (active) setLabError('Unable to load Lab data.');
      });
    const disconnect = connectLabEvents(event => {
      setActivityEvents(previous => [event, ...previous].slice(0, 100));
      getObservability()
        .then(snapshot => active && setLabData(snapshot))
        .catch(() => active && setLabError('Lab updates disconnected.'));
    }, () => active && setLabError('Lab updates disconnected.'));
    return () => {
      active = false;
      disconnect();
    };
  }, [labOpen]);

  const playVoiceResponse = async audioSource => {
    if (!audioSource) return;
    audioRef.current?.pause();
    const audio = new Audio(audioSource);
    audioRef.current = audio;
    try {
      await audio.play();
    } catch {
      setError('Voice response is ready, but audio playback was blocked.');
    }
  };

  const stopListening = () => {
    processorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
    audioContextRef.current?.close();
    socketRef.current?.close();
    processorRef.current = null;
    audioSourceRef.current = null;
    mediaStreamRef.current = null;
    audioContextRef.current = null;
    socketRef.current = null;
    setListening(false);
  };

  const startListening = async () => {
    setError('');
    setInterimTranscript('');

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access is not supported in this browser.');
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const websocketUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/api/voice/listen?session_id=${encodeURIComponent(sessionId)}&user_id=${encodeURIComponent(userId)}`;
    const socket = new WebSocket(websocketUrl);
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    socket.onopen = () => {
      setListening(true);
      setConnectionStatus('Listening');
      source.connect(processor);
      processor.connect(audioContext.destination);
    };
    socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.error) {
        setError(message.error);
        stopListening();
      } else if (message.processing) {
        setProcessing(false);
        setAssistantResponse(message.processing.text || message.processing.response);
        setExecutionEvents(message.processing.task_result?.output?.events || []);
        if (message.processing.tts_error) setError(message.processing.tts_error);
        if (message.processing.response_type === 'voice') {
          void playVoiceResponse(message.processing.audio);
        }
        setConnectionStatus('Ready');
      } else if (message.is_final) {
        setTranscript(previous => `${previous} ${message.transcript}`.trim());
        setInterimTranscript('');
        setProcessing(true);
      } else {
        setInterimTranscript(message.transcript);
      }
    };
    socket.onerror = () => {
      setError('Could not connect to the voice service.');
      stopListening();
    };
    socket.onclose = () => {
      if (socketRef.current === socket) {
        setConnectionStatus('Ready');
        stopListening();
      }
    };
    processor.onaudioprocess = event => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(toPcm16(event.inputBuffer.getChannelData(0), audioContext.sampleRate));
      }
    };

    socketRef.current = socket;
    audioContextRef.current = audioContext;
    mediaStreamRef.current = stream;
    audioSourceRef.current = source;
    processorRef.current = processor;
  };

  const submitText = async event => {
    event.preventDefault();
    const message = textInput.trim();
    if (!message || processing) return;
    setError('');
    setProcessing(true);
    setTranscript(message);
    setInterimTranscript('');
    try {
      const result = await submitChat({ transcript: message, session_id: sessionId, user_id: userId, input_type: 'text' });
      setAssistantResponse(result.text || result.response);
      setExecutionEvents(result.task_result?.output?.events || []);
      if (result.response_type === 'voice') {
        void playVoiceResponse(result.audio);
      }
      setConnectionStatus('Ready');
      setTextInput('');
    } catch {
      setError('Could not process that request.');
    } finally {
      setProcessing(false);
    }
  };

  const toggleMic = async () => {
    setPulseAnim(true);
    setTimeout(() => setPulseAnim(false), 600);
    if (listening) {
      stopListening();
      setConnectionStatus('Ready');
      return;
    }

    try {
      await startListening();
    } catch (startError) {
      stopListening();
      setError(startError.name === 'NotAllowedError'
        ? 'Microphone permission was denied.'
        : 'Could not start the microphone.');
    }
  };

  return (
    <div className="evi-root">
      {/* ── Main content area ── */}
      <main className="evi-main">
        {/* Background wave decorations */}
        <div className="bg-wave bg-wave-1" />
        <div className="bg-wave bg-wave-2" />

        {/* Top-Right Header Controls: EVI Lab & Background Toggle */}
        <div className="evi-top-bar">
          <button 
            type="button"
            className="evi-lab-btn" 
            onClick={() => setLabOpen(true)}
            title="Open EVI Lab"
          >
            <FlaskIcon />
            <span>EVI Lab</span>
          </button>

          <div className="evi-bg-toggle-container">
            <span className="evi-bg-toggle-label">Background</span>
            <button 
              type="button"
              className={`evi-switch ${backgroundEnabled ? 'evi-switch-on' : 'evi-switch-off'}`}
              onClick={() => setBackgroundEnabled(prev => !prev)}
              aria-pressed={backgroundEnabled}
              title={backgroundEnabled ? "Disable background working" : "Enable background working"}
            >
              <span className="evi-switch-track">
                {backgroundEnabled ? 'ON' : ''}
              </span>
              <span className="evi-switch-thumb" />
            </button>
          </div>
        </div>

        {/* Avatar section */}
        <div className="evi-avatar-section">
          <div className="avatar-sparkle avatar-sparkle-left">✦</div>
          <div className="avatar-wrapper">
            <img
              src="/evi_character.jpg"
              alt="EVI assistant character"
              className="evi-avatar"
              draggable="false"
            />
          </div>
          <div className="avatar-heart">♡</div>
        </div>

        {/* Greeting */}
        <div className="evi-greeting">
          <h1 className="evi-title">
            Hi, I'm <span className="evi-name">EVI</span>
          </h1>
          <p className="evi-subtitle">
            Your AI desktop assistant.&nbsp; I'm here to help you,
            <br />
            just say what you need or click the mic.
          </p>
        </div>

        <div className="connection-status" role="status">
          <span className={`status-dot ${connectionStatus === 'Listening' ? 'status-listening' : ''}`} />
          {connectionStatus}
        </div>

        {(transcript || interimTranscript || error) && (
          <div className="transcript" aria-live="polite">
            {error ? <div className="transcript-error">{error}</div> : (
              <>
                {transcript && (
                  <div className="message-row message-user">
                    <span className="message-label">You</span>
                    <span>{transcript}</span>
                  </div>
                )}
                {interimTranscript && (
                  <div className="message-row message-interim">
                    <span className="message-label">Listening</span>
                    <span>{interimTranscript}</span>
                  </div>
                )}
                {assistantResponse && (
                  <div className="message-row message-assistant">
                    <span className="message-label">EVI</span>
                    <span>{assistantResponse}</span>
                  </div>
                )}
                {executionEvents.length > 0 && (
                  <div className="execution-events" aria-label="Task progress">
                    {executionEvents.map(event => (
                      <div className="execution-event" key={`${event.step_id}-${event.status}`}>
                        <span>{event.agent}</span>
                        <span>{event.action}</span>
                        <span>{event.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        <form className="text-input-form" onSubmit={submitText}>
          <input
            value={textInput}
            onChange={event => setTextInput(event.target.value)}
            placeholder="Type a message to EVI"
            aria-label="Message EVI"
          />
          <button type="submit" disabled={processing || !textInput.trim()}>Send</button>
        </form>

        {/* Mic button */}
        <div className="mic-container">
          {listening && <div className="mic-ripple" />}
          <button
            id="mic-btn"
            className={`mic-btn ${listening ? 'mic-active' : ''} ${pulseAnim ? 'mic-pulse' : ''}`}
            onClick={toggleMic}
            title={listening ? 'Stop listening' : 'Start listening'}
            aria-label="Microphone"
          >
            <MicIcon />
          </button>
        </div>

        {/* Footer */}
        <footer className="evi-footer">
          Ready when you are&nbsp;<span className="footer-heart">🧡</span>
        </footer>

        {/* Bottom-Right Floating Background Working Badge */}
        {backgroundEnabled && (
          <button 
            type="button"
            className="evi-bg-floating-badge"
            onClick={() => {
              setLabTab('overview');
              setLabOpen(true);
            }}
            title="Click to open background tasks in EVI Lab"
          >
            <span className="evi-bg-pulse-dot" />
            <span>EVI is working in background</span>
          </button>
        )}

        {/* EVI Lab Modal Overlay */}
        {labOpen && (
          <div className="evi-lab-overlay" onClick={() => setLabOpen(false)}>
            <div className="evi-lab-modal" onClick={e => e.stopPropagation()}>
              <div className="evi-lab-header">
                <div className="evi-lab-title">
                  <FlaskIcon />
                  <h2>EVI Lab</h2>
                  <span className="evi-lab-status-badge">
                    <span className="status-dot status-listening" /> {backgroundEnabled ? "Background Service Active" : "Standby"}
                  </span>
                </div>
                <button className="evi-lab-close-btn" onClick={() => setLabOpen(false)} aria-label="Close EVI Lab">✕</button>
              </div>

              <div className="evi-lab-tabs">
                {LAB_TABS.map(([id, label]) => (
                  <button
                    key={id}
                    className={`evi-lab-tab ${labTab === id ? 'active' : ''}`}
                    onClick={() => setLabTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="evi-lab-content">
                {labTab === 'overview' && (
                  <div className="lab-card">
                    <div className="lab-card-header">
                      <h3>Background Orchestration</h3>
                      <span className="lab-tag green">{backgroundEnabled ? "Running" : "Paused"}</span>
                    </div>
                    {labError && <p className="lab-desc transcript-error">{labError}</p>}
                    {!labData && !labError && <p className="lab-desc">Loading Lab data...</p>}
                    <div className="lab-stats">
                      <div className="stat-box">
                        <div className="stat-label">Background Working</div>
                        <div className="stat-val">{backgroundEnabled ? "Enabled (ON)" : "Disabled (OFF)"}</div>
                      </div>
                      <div className="stat-box">
                        <div className="stat-label">Desktop Agent</div>
                        <div className="stat-val">{labData ? `${labData.agents.length} registered` : 'Loading...'}</div>
                      </div>
                      <div className="stat-box">
                        <div className="stat-label">Active Session</div>
                        <div className="stat-val">{labData ? `${labData.overview.tasks.running} running` : 'Loading...'}</div>
                      </div>
                    </div>

                    <div className="lab-tasks-list">
                      {labData?.tasks.slice(0, 5).map(task => (
                        <div className="lab-task-item" key={task.task_id}>
                          <div><strong>{task.agent}</strong> — {task.action || task.task_type}</div>
                          <span className="lab-task-status">{task.status}</span>
                        </div>
                      ))}
                      {!labData?.tasks.length && labData && <div className="lab-task-item">No tasks yet.</div>}
                    </div>
                  </div>
                )}

                {labTab === 'agents' && (
                  <div className="lab-card">
                    <div className="lab-card-header">
                      <h3>Registered Agents</h3>
                      <span className="lab-tag green">{labData ? `${labData.agents.length} Connected` : 'Loading...'}</span>
                    </div>
                    <div className="lab-tasks-list">
                      {labData?.agents.map(agent => (
                        <div className="lab-task-item" key={agent.id}>
                          <div><strong>{agent.name}</strong></div>
                          <span className="lab-task-status">{agent.status}</span>
                        </div>
                      ))}
                      {!labData?.agents.length && labData && <div className="lab-task-item">No registered agents.</div>}
                    </div>
                  </div>
                )}

                {labTab === 'overview' && (
                  <div className="lab-card">
                    <div className="lab-card-header">
                      <h3>Desktop Capability Registry</h3>
                      <span className="lab-tag green">{labData?.health?.status || 'Loading...'}</span>
                    </div>
                    <p className="lab-desc">Live component health from the EVI backend:</p>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '9px', fontSize: '12.5px', color: '#4a382b' }}>
                      {Object.entries(labData?.health?.components || {}).map(([component, status]) => (
                        <div key={component}>● <strong>{component}</strong> — {status}</div>
                      ))}
                      {labData?.llm && <div>● <strong>LLM</strong> — {labData.llm.provider || 'not used'} / {labData.llm.active_model || 'no response yet'}</div>}
                      {!labData?.health && <div>Loading component health...</div>}
                    </div>
                  </div>
                )}

                {labTab === 'tasks' && <LabExtendedPanel tab="tasks" data={labData} activityEvents={activityEvents} />}
                {labTab !== 'overview' && labTab !== 'agents' && labTab !== 'tasks' && (
                  <LabExtendedPanel tab={labTab} data={labData} activityEvents={activityEvents} />
                )}

              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
