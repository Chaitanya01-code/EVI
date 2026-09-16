const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function get(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`Lab request failed: ${response.status}`);
  return response.json();
}

export const getLabOverview = () => get('/api/lab/overview');
export const getAgents = () => get('/api/lab/agents');
export const getAgent = agentId => get(`/api/lab/agents/${encodeURIComponent(agentId)}`);
export const getAgentActivity = (agentId, limit = 20, offset = 0) => get(`/api/lab/agents/${encodeURIComponent(agentId)}/activity?limit=${limit}&offset=${offset}`);
export const getTasks = (limit = 20) => get(`/api/lab/tasks?limit=${limit}`);
export const getTask = taskId => get(`/api/lab/tasks/${encodeURIComponent(taskId)}`);
export const getTaskSteps = taskId => get(`/api/lab/tasks/${encodeURIComponent(taskId)}/steps`);
export const getConversations = (limit = 20, offset = 0) => get(`/api/lab/conversations?limit=${limit}&offset=${offset}`);
export const getConversation = (conversationId, limit = 50, offset = 0) => get(`/api/lab/conversations/${encodeURIComponent(conversationId)}?limit=${limit}&offset=${offset}`);
export const getMemory = (limit = 20, offset = 0) => get(`/api/lab/memory?limit=${limit}&offset=${offset}`);
export const getExecutions = (limit = 20, offset = 0) => get(`/api/lab/executions?limit=${limit}&offset=${offset}`);
export const getSystemHealth = () => get('/api/lab/system/health');

export function connectLabEvents(onEvent, onError) {
  const events = new EventSource(`${API_BASE_URL}/api/lab/events`);
  const eventNames = ['task_created', 'task_started', 'task_completed', 'task_failed', 'step_started', 'step_completed', 'step_failed', 'agent_status_changed'];
  eventNames.forEach(name => events.addEventListener(name, event => onEvent({ ...JSON.parse(event.data), event: name })));
  events.onerror = onError;
  return () => events.close();
}
