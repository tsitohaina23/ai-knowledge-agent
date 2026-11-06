// Typed client for the local FastAPI backend.

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface Source {
  n: number;
  source: string;
  page: number;
  score: number;
  excerpt: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  refused: boolean;
  provider: string;
  model: string;
  latency_ms: { retrieval: number; generation: number; total: number };
  tokens: { input: number; output: number; total: number };
  cost_usd: number;
  cached: boolean;
  warnings: string[];
}

export interface Health {
  status: string;
  provider: string;
  model: string;
  vector_store: string;
  embedding_model: string;
  indexed_chunks: number;
}

export interface IngestResponse {
  source: string;
  pages: number;
  chunks: number;
  added: number;
  seconds: number;
  total_chunks: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const getHealth = () => request<Health>('/health');

export const ingestSample = () => request<IngestResponse>('/ingest/sample', { method: 'POST' });

export const ask = (question: string) =>
  request<AskResponse>('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

/** Upload a PDF and report progress from the Server-Sent Events stream. */
export async function uploadWithProgress(
  file: File,
  onProgress: (pct: number, message: string) => void,
): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_URL}/upload-stream`, { method: 'POST', body: form });
  if (!res.ok || !res.body) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? ''; // keep an incomplete event for the next read
    for (const event of events) {
      if (!event.startsWith('data: ')) continue;
      const data = JSON.parse(event.slice(6));
      if (data.error) throw new Error(data.error);
      if (data.progress !== undefined) onProgress(data.progress, data.message);
    }
  }
}
