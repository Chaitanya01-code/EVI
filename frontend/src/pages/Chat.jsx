import React, { useState } from 'react';
import { sendCommand } from '../services/api.js';
import VoiceInput from '../components/voice/VoiceInput.jsx';
import VoiceOutput from '../components/voice/VoiceOutput.jsx';

export default function ChatPage() {
  const [message, setMessage] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const runCommand = async () => {
    const transcript = message.trim();
    if (!transcript || pending) return;
    setPending(true);
    setError('');
    try {
      setResult(await sendCommand(transcript, 'Assistant text command'));
    } catch (commandError) {
      setError(commandError.message);
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="page-content-wrapper chat-view">
      <div className="chat-layout">
        <div className="chat-main">
          <div className="chat-header">
            <h2>AI Assistant</h2>
            <p className="subtitle">Your intelligent companion powered by advanced AI models</p>
          </div>
          
          <div className="chat-welcome">
            <div className="robot-icon">🤖</div>
            <p className="welcome-text">Hello! I'm your AI assistant. I can help you with:</p>
            <ul className="capabilities-list">
              <li>Answer questions</li>
              <li>Analyze documents</li>
              <li>Write code</li>
              <li>Browse the web</li>
              <li>Manage files</li>
              <li>And much more...</li>
            </ul>
          </div>
          
          <div className="chat-input-area">
            <div className="input-box">
              <input type="text" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && runCommand()} placeholder="Type your message..." aria-label="NOVA command" />
              <div className="input-actions">
                <button className="icon-btn">📎</button>
                <button className="icon-btn" onClick={() => document.getElementById('nova-voice-control')?.scrollIntoView()}>🎤</button>
                <button className="send-btn" onClick={runCommand} disabled={pending}>{pending ? '…' : '▶'}</button>
              </div>
            </div>
          </div>
          {error && <div className="voice-error">{error}</div>}
          <VoiceOutput response={result} />
          <div id="nova-voice-control"><VoiceInput context="Assistant voice command" onResponse={setResult} /></div>
        </div>

        <div className="chat-sidebar">
          <div className="sidebar-section">
            <h3>Available Agents</h3>
            <ul className="agent-list">
              <li className="agent-item">
                <div className="agent-icon browser">🌐</div>
                <div className="agent-info">
                  <span className="agent-name">Browser Agent</span>
                  <span className="agent-desc">Web browsing & research</span>
                </div>
              </li>
              <li className="agent-item">
                <div className="agent-icon computer">💻</div>
                <div className="agent-info">
                  <span className="agent-name">Computer Agent</span>
                  <span className="agent-desc">OS operations & automation</span>
                </div>
              </li>
              <li className="agent-item">
                <div className="agent-icon file">📁</div>
                <div className="agent-info">
                  <span className="agent-name">File Agent</span>
                  <span className="agent-desc">File management & analysis</span>
                </div>
              </li>
              <li className="agent-item">
                <div className="agent-icon coding">⌨️</div>
                <div className="agent-info">
                  <span className="agent-name">Coding Agent</span>
                  <span className="agent-desc">Code generation & debugging</span>
                </div>
              </li>
              <li className="agent-item">
                <div className="agent-icon research">🔍</div>
                <div className="agent-info">
                  <span className="agent-name">Research Agent</span>
                  <span className="agent-desc">Deep research & analysis</span>
                </div>
              </li>
            </ul>
          </div>

          <div className="sidebar-section">
            <h3>Quick Actions</h3>
            <ul className="action-list">
              <li className="action-item"><span className="action-icon">🌐</span> Browse the web</li>
              <li className="action-item"><span className="action-icon">📁</span> Analyze a file</li>
              <li className="action-item"><span className="action-icon">⌨️</span> Generate code</li>
              <li className="action-item"><span className="action-icon">🔍</span> Search knowledge</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
