import Cookies from 'js-cookie';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(): string | undefined {
  return Cookies.get('token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

function fileHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

async function handleResponse(res: Response) {
  if (res.status === 401) {
    Cookies.remove('token');
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(data.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function apiGet(path: string) {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'GET', headers: authHeaders() });
  return handleResponse(res);
}

export async function apiPost(path: string, body?: unknown) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST', headers: authHeaders(), body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse(res);
}

export async function apiPut(path: string, body?: unknown) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'PUT', headers: authHeaders(), body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse(res);
}

export async function apiDelete(path: string) {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'DELETE', headers: authHeaders() });
  return handleResponse(res);
}

export async function apiUpload(path: string, formData: FormData) {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers: fileHeaders(), body: formData });
  return handleResponse(res);
}

export async function apiPostDownload(path: string, body?: unknown): Promise<Blob> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST', headers: authHeaders(), body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error('Download failed');
  return res.blob();
}

// ============== AUTH ==============
export const auth = {
  register: (data: { full_name: string; email: string; password: string }) =>
    apiPost('/api/auth/register', data),
  login: (data: { email: string; password: string }) =>
    apiPost('/api/auth/login', data),
  getProfile: () => apiGet('/api/auth/me'),
};

// ============== COLLECTIONS ==============
export const collectionsApi = {
  list: () => apiGet('/api/collections'),
  create: (data: { name: string; description?: string }) =>
    apiPost('/api/collections', data),
  get: (id: number) => apiGet(`/api/collections/${id}`),
  update: (id: number, data: { name?: string; description?: string }) =>
    apiPut(`/api/collections/${id}`, data),
  delete: (id: number) => apiDelete(`/api/collections/${id}`),
};

// ============== SOURCES ==============
export const sourcesApi = {
  upload: (collectionId: number, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return apiUpload(`/api/collections/${collectionId}/sources/upload`, formData);
  },
  addUrl: (collectionId: number, url: string, title?: string) =>
    apiPost(`/api/collections/${collectionId}/sources/url`, { url, title }),
  addYoutube: (collectionId: number, url: string, title?: string) =>
    apiPost(`/api/collections/${collectionId}/sources/youtube`, { url, title }),
  list: (collectionId: number) =>
    apiGet(`/api/collections/${collectionId}/sources`),
  delete: (sourceId: number) => apiDelete(`/api/sources/${sourceId}`),
  reprocess: (sourceId: number) => apiPost(`/api/sources/${sourceId}/reprocess`),
};

// ============== CHAT ==============
export const chatApi = {
  listSessions: (collectionId: number) =>
    apiGet(`/api/collections/${collectionId}/chat/sessions`),
  createSession: (collectionId: number, title?: string) =>
    apiPost(`/api/collections/${collectionId}/chat/sessions`, { title }),
  getMessages: (sessionId: number) =>
    apiGet(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: number, content: string) =>
    apiPost(`/api/chat/sessions/${sessionId}/messages`, { content }),
  deleteSession: (sessionId: number) =>
    apiDelete(`/api/chat/sessions/${sessionId}`),
};

// ============== STUDY ==============
export const studyApi = {
  generate: (collectionId: number, type: string, source_ids?: number[]) =>
    apiPost(`/api/collections/${collectionId}/generate`, { type, source_ids }),
  listGenerated: (collectionId: number, content_type?: string) => {
    const q = content_type ? `?content_type=${content_type}` : '';
    return apiGet(`/api/collections/${collectionId}/generated${q}`);
  },
  getGenerated: (id: number) => apiGet(`/api/generated/${id}`),
  deleteGenerated: (id: number) => apiDelete(`/api/generated/${id}`),
};

// ============== FLASHCARDS ==============
export const flashcardsApi = {
  list: (collectionId: number, favoritesOnly?: boolean) => {
    const q = favoritesOnly ? '?favorites_only=true' : '';
    return apiGet(`/api/collections/${collectionId}/flashcards${q}`);
  },
  create: (collectionId: number, data: { question: string; answer: string }) =>
    apiPost(`/api/collections/${collectionId}/flashcards`, data),
  toggleFavorite: (id: number) => apiPut(`/api/flashcards/${id}/toggle-favorite`),
  delete: (id: number) => apiDelete(`/api/flashcards/${id}`),
};

// ============== QUESTIONS ==============
export const questionsApi = {
  deduplicateDocuments: (collectionId: number, source_ids: number[]) =>
    apiPost(`/api/collections/${collectionId}/deduplicate-documents`, { source_ids }),
  exportDeduplicatedDocuments: (collectionId: number, source_ids: number[], format: string) =>
    apiPostDownload(`/api/collections/${collectionId}/deduplicate-documents/export?format=${format}`, { source_ids }),
  detectDuplicates: (collectionId: number, data?: { similarity_threshold?: number; use_llm_verification?: boolean }) =>
    apiPost(`/api/collections/${collectionId}/detect-duplicates`, data),
  getQuestions: (collectionId: number, params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return apiGet(`/api/collections/${collectionId}/questions${q}`);
  },
  getDuplicateGroups: (collectionId: number, params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return apiGet(`/api/collections/${collectionId}/duplicate-groups${q}`);
  },
  getQuestionStats: (collectionId: number) =>
    apiGet(`/api/collections/${collectionId}/question-stats`),
  exportQuestions: (collectionId: number, format: string) =>
    apiPost(`/api/collections/${collectionId}/export-questions?format=${format}`),
  mergeGroups: (groupIds: number[]) =>
    apiPost('/api/duplicate-groups/merge', { group_ids: groupIds }),
  removeFromGroup: (groupId: number, questionId: number) =>
    apiPost(`/api/duplicate-groups/${groupId}/remove-question`, { question_id: questionId }),
};

// ============== QUIZ ==============
export const quizApi = {
  generate: (collectionId: number, data: { question_count: number; difficulty: string; question_type: string; source_ids?: number[] }) =>
    apiPost(`/api/collections/${collectionId}/quiz/generate`, data),
  submit: (data: { collection_id: number; title?: string; difficulty?: string; questions_json: any[]; answers_json: any[]; time_taken_seconds?: number }) =>
    apiPost('/api/quiz/submit', data),
  history: () => apiGet('/api/quiz/history'),
  getDetail: (id: number) => apiGet(`/api/quiz/${id}`),
};

// ============== DASHBOARD ==============
export const dashboardApi = {
  stats: () => apiGet('/api/dashboard/stats'),
  recentActivity: () => apiGet('/api/dashboard/recent-activity'),
};

// ============== EXPORT ==============
export const exportApi = {
  pdf: (data: { content_type: string; content_id?: number; collection_id?: number; title?: string }) =>
    apiPostDownload('/api/export/pdf', data),
  docx: (data: { content_type: string; content_id?: number; collection_id?: number; title?: string }) =>
    apiPostDownload('/api/export/docx', data),
  txt: (data: { content_type: string; content_id?: number; collection_id?: number; title?: string }) =>
    apiPostDownload('/api/export/txt', data),
};
