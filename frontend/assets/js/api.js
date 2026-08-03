/**
 * VICTORUS AI — API Client
 * Central fetch wrapper: attaches JWT, handles refresh, parses errors.
 */
const API_BASE = (() => {
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000/api/v1`;
})();

const Storage = {
  get access() { return localStorage.getItem('victorus_access_token'); },
  set access(v) { v ? localStorage.setItem('victorus_access_token', v) : localStorage.removeItem('victorus_access_token'); },
  get refresh() { return localStorage.getItem('victorus_refresh_token'); },
  set refresh(v) { v ? localStorage.setItem('victorus_refresh_token', v) : localStorage.removeItem('victorus_refresh_token'); },
  get user() { try { return JSON.parse(localStorage.getItem('victorus_user') || 'null'); } catch { return null; } },
  set user(v) { v ? localStorage.setItem('victorus_user', JSON.stringify(v)) : localStorage.removeItem('victorus_user'); },
  clear() { this.access = null; this.refresh = null; this.user = null; },
};

async function apiRequest(path, { method = 'GET', body, auth = true, isForm = false } = {}) {
  const headers = {};
  if (!isForm) headers['Content-Type'] = 'application/json';
  if (auth && Storage.access) headers['Authorization'] = `Bearer ${Storage.access}`;

  const opts = { method, headers };
  if (body) opts.body = isForm ? body : JSON.stringify(body);

  let res = await fetch(`${API_BASE}${path}`, opts);

  // Auto-refresh once on 401
  if (res.status === 401 && auth && Storage.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${Storage.access}`;
      res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
    }
  }

  let data = null;
  try { data = await res.json(); } catch { /* no body */ }

  if (!res.ok) {
    const message = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return data;
}

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: Storage.refresh }),
    });
    if (!res.ok) throw new Error('refresh failed');
    const data = await res.json();
    Storage.access = data.access_token;
    return true;
  } catch {
    Storage.clear();
    return false;
  }
}

const Api = {
  // Auth
  register: (payload) => apiRequest('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => apiRequest('/auth/login', { method: 'POST', body: payload, auth: false }),
  logout: () => apiRequest('/auth/logout', { method: 'POST', body: { refresh_token: Storage.refresh }, auth: false }),
  logoutAll: () => apiRequest('/auth/logout-all', { method: 'POST' }),
  me: () => apiRequest('/auth/me'),
  forgotPassword: (email) => apiRequest('/auth/forgot-password', { method: 'POST', body: { email }, auth: false }),
  resetPassword: (token, new_password) => apiRequest('/auth/reset-password', { method: 'POST', body: { token, new_password }, auth: false }),
  changePassword: (payload) => apiRequest('/auth/change-password', { method: 'POST', body: payload }),
  verifyOtp: (email, otp_code) => apiRequest('/auth/verify-otp', { method: 'POST', body: { email, otp_code }, auth: false }),
  resendOtp: (email) => apiRequest('/auth/resend-otp', { method: 'POST', body: { email }, auth: false }),

  // Onboarding
  autocompleteSkills: (q) => apiRequest(`/onboarding/skills/autocomplete?q=${encodeURIComponent(q)}`),
  completeOnboarding: (payload) => apiRequest('/onboarding/complete', { method: 'POST', body: payload }),
  uploadResume: (formData) => apiRequest('/onboarding/upload-resume', { method: 'POST', body: formData, isForm: true }),

  // Profile
  getProfile: () => apiRequest('/profile/me'),
  updateProfile: (payload) => apiRequest('/profile/me', { method: 'PUT', body: payload }),
  uploadAvatar: (formData) => apiRequest('/profile/avatar', { method: 'POST', body: formData, isForm: true }),

  // Dashboard
  overview: () => apiRequest('/dashboard/overview'),
 recommendations: () => apiRequest('/dashboard/recommendations'),
 // Memory
  listMemory: () => apiRequest('/memory'),
  createMemory: (payload) => apiRequest('/memory', { method: 'POST', body: payload }),
  updateMemory: (id, payload) => apiRequest(`/memory/${id}`, { method: 'PUT', body: payload }),
  deleteMemory: (id) => apiRequest(`/memory/${id}`, { method: 'DELETE' }),

  // Conversations
  listConversations: () => apiRequest('/conversations'),
  createConversation: (payload) => apiRequest('/conversations', { method: 'POST', body: payload }),
  getConversation: (id) => apiRequest(`/conversations/${id}`),
  deleteConversation: (id) => apiRequest(`/conversations/${id}`, { method: 'DELETE' }),
  sendMessage: (id, content) => apiRequest(`/conversations/${id}/messages`, { method: 'POST', body: { content } }),

  // Agents
  listAgents: () => apiRequest('/agents'),
  toggleAgent: (agent_key, is_enabled) => apiRequest('/agents/toggle', { method: 'POST', body: { agent_key, is_enabled } }),

  // Tasks
  listTasks: (status) => apiRequest(`/tasks${status ? `?status=${status}` : ''}`),
  createTask: (payload) => apiRequest('/tasks', { method: 'POST', body: payload }),
  updateTask: (id, payload) => apiRequest(`/tasks/${id}`, { method: 'PATCH', body: payload }),
  deleteTask: (id) => apiRequest(`/tasks/${id}`, { method: 'DELETE' }),

  // Files
  listFiles: (params = '') => apiRequest(`/files${params}`),
  uploadFile: (formData) => apiRequest('/files', { method: 'POST', body: formData, isForm: true }),
  renameFile: (id, new_name) => apiRequest(`/files/${id}`, { method: 'PATCH', body: { new_name } }),
  deleteFile: (id) => apiRequest(`/files/${id}`, { method: 'DELETE' }),

  // Notifications
  listNotifications: (unreadOnly = false) => apiRequest(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),
  unreadCount: () => apiRequest('/notifications/unread-count'),
  markRead: (id) => apiRequest(`/notifications/${id}/read`, { method: 'PATCH' }),
  markAllRead: () => apiRequest('/notifications/read-all', { method: 'PATCH' }),
  deleteNotification: (id) => apiRequest(`/notifications/${id}`, { method: 'DELETE' }),

  // Settings
  getSettings: () => apiRequest('/settings'),
  updateSettings: (payload) => apiRequest('/settings', { method: 'PUT', body: payload }),
  deleteAccount: () => apiRequest('/settings/account', { method: 'DELETE' }),

  // Security
  listSessions: () => apiRequest('/security/sessions'),
  revokeSession: (id) => apiRequest(`/security/sessions/${id}`, { method: 'DELETE' }),
  activityLogs: () => apiRequest('/security/activity-logs'),

  // API Keys
  listApiKeys: () => apiRequest('/api-keys'),
  createApiKey: (name) => apiRequest('/api-keys', { method: 'POST', body: { name } }),
  revokeApiKey: (id) => apiRequest(`/api-keys/${id}`, { method: 'DELETE' }),

  // Integrations
  listIntegrations: () => apiRequest('/integrations'),
  toggleIntegration: (provider) => apiRequest(`/integrations/${provider}/toggle`, { method: 'POST' }),
};
