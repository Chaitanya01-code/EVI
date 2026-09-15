const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export async function sendVoiceTranscript(transcript, context = '') {
  return sendCommand(transcript, context);
}

export async function sendCommand(transcript, context = '') {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      transcript,
      context,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Command failed with ${response.status}: ${detail}`);
  }

  return response.json();
}

export async function listInstalledApps() {
  const response = await fetch(`${API_BASE}/api/applications/installed`, {
    method: 'GET',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`List installed apps failed with ${response.status}: ${detail}`);
  }
  return response.json();
}

export async function openAllApplications(context = '') {
  const response = await fetch(`${API_BASE}/api/applications/open-all`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({context}),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Open all apps failed with ${response.status}: ${detail}`);
  }
  return response.json();
}

export async function launchApplication(appName, context = '') {
  return sendCommand(`open ${appName}`, context);
}

export async function closeApplication(appName, context = '') {
  return sendCommand(`close ${appName}`, context);
}
