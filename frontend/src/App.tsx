import { useCallback, useEffect, useRef, useState } from 'react';
import type React from 'react';
import {
  ask,
  getHealth,
  ingestSample,
  uploadWithProgress,
  type AskResponse,
  type Health,
} from './api';

interface Message {
  id: string;
  question: string;
  result?: AskResponse;
  error?: string;
  isCollapsed: boolean;
  isEditing: boolean;
}

const EXAMPLES = [
  'Combien de jours de congés payés par an ?',
  "Quel est le plafond de remboursement d'un repas d'affaires ?",
  'Quelle est la capitale du Japon ?',
];

function SourceList({ result }: { result: AskResponse }) {
  if (result.sources.length === 0) return null;
  return (
    <details className="mt-2 text-xs text-gray-600">
      <summary className="cursor-pointer select-none">
        Sources ({result.sources.length}) : pages{' '}
        {[...new Set(result.sources.map((s) => s.page))].join(', ')}
      </summary>
      <ul className="mt-2 space-y-2">
        {result.sources.map((s) => (
          <li key={s.n} className="rounded border border-gray-200 bg-white p-2">
            <div className="font-semibold text-gray-700">
              [{s.n}] {s.source} · p. {s.page} · similarité {s.score.toFixed(2)}
            </div>
            <div className="mt-1 text-gray-600">{s.excerpt}</div>
          </li>
        ))}
      </ul>
    </details>
  );
}

function Metrics({ result }: { result: AskResponse }) {
  return (
    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-gray-500">
      <span className="rounded bg-gray-100 px-2 py-0.5">{result.latency_ms.total.toFixed(0)} ms</span>
      <span className="rounded bg-gray-100 px-2 py-0.5">{result.tokens.total} tokens</span>
      <span className="rounded bg-gray-100 px-2 py-0.5">
        {result.provider === 'none' ? 'mode extraits (sans LLM)' : `${result.provider} · ${result.model}`}
      </span>
      <span className="rounded bg-gray-100 px-2 py-0.5">coût 0 $ (local)</span>
      {result.cached && <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">cache</span>}
      {result.warnings.map((w) => (
        <span key={w} className="rounded bg-red-100 px-2 py-0.5 text-red-700">
          {w}
        </span>
      ))}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [backendError, setBackendError] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [inputQuestion, setInputQuestion] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await getHealth());
      setBackendError('');
    } catch {
      setBackendError('Backend injoignable : lancez « uvicorn app.main:app » dans backend/.');
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setProgress(0);
    setUploadStatus('Envoi du fichier au serveur...');
    try {
      await uploadWithProgress(file, (pct, msg) => {
        setProgress(pct);
        setUploadStatus(msg);
      });
    } catch (err) {
      setUploadStatus(`Erreur : ${(err as Error).message}`);
    } finally {
      setIsUploading(false);
      void refreshHealth();
    }
  };

  const handleSample = async () => {
    setIsUploading(true);
    setUploadStatus("Indexation du PDF d'exemple...");
    try {
      const r = await ingestSample();
      setUploadStatus(`${r.source} : ${r.pages} pages, ${r.chunks} blocs indexés en ${r.seconds} s.`);
    } catch (err) {
      setUploadStatus(`Erreur : ${(err as Error).message}`);
    } finally {
      setIsUploading(false);
      void refreshHealth();
    }
  };

  const sendQuestion = async (questionText: string, messageIdToReplace?: string) => {
    if (!questionText.trim() || loading) return;
    setLoading(true);
    let result: AskResponse | undefined;
    let error: string | undefined;
    try {
      result = await ask(questionText);
    } catch (err) {
      error = (err as Error).message;
    }
    if (messageIdToReplace) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageIdToReplace
            ? { ...m, question: questionText, result, error, isEditing: false, isCollapsed: false }
            : m,
        ),
      );
    } else {
      setMessages((prev) => [
        ...prev.map((m) => ({ ...m, isCollapsed: true })),
        { id: Date.now().toString(), question: questionText, result, error, isCollapsed: false, isEditing: false },
      ]);
      setInputQuestion('');
    }
    setLoading(false);
  };

  const toggle = (id: string, key: 'isCollapsed' | 'isEditing') =>
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, [key]: !m[key] } : m)));

  return (
    <div className="flex min-h-screen flex-col items-center p-4 sm:p-6">
      <div className="w-full max-w-3xl space-y-5 rounded-xl bg-white p-5 shadow-md sm:p-6">
        <header className="text-center">
          <h1 className="text-2xl font-bold text-gray-800">AI Knowledge Agent</h1>
          <p className="mt-1 text-sm text-gray-500">
            Posez des questions sur vos PDF : réponses avec pages sources, 100 % local.
          </p>
          {health && (
            <p className="mt-2 text-xs text-gray-500">
              {health.vector_store} · {health.indexed_chunks} blocs indexés ·{' '}
              {health.provider === 'none' ? 'mode extraits' : `${health.provider} (${health.model})`}
            </p>
          )}
          {backendError && <p className="mt-2 text-xs font-medium text-red-600">{backendError}</p>}
        </header>

        <section className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-4 text-center">
          <h2 className="mb-2 font-semibold text-gray-700">1. Importer un document PDF</h2>
          <div className="mb-3 flex flex-wrap items-center justify-center gap-3">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={isUploading}
              className="text-sm text-gray-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-blue-700 hover:file:bg-blue-100"
            />
            <button
              onClick={handleUpload}
              disabled={isUploading || !file}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              Charger le PDF
            </button>
            <button
              onClick={handleSample}
              disabled={isUploading}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
            >
              Utiliser le PDF d'exemple
            </button>
          </div>
          {isUploading && progress > 0 && (
            <div className="w-full space-y-1">
              <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
                <div className="h-3 bg-blue-600 transition-all duration-200 ease-out" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-right text-xs font-bold text-blue-600">{progress}%</div>
            </div>
          )}
          {uploadStatus && <p className="mt-2 text-xs font-medium text-blue-800">{uploadStatus}</p>}
        </section>

        <section className="max-h-[520px] space-y-4 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  onClick={() => sendQuestion(q)}
                  className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-800 hover:bg-blue-100"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {messages.map((item) => (
            <div key={item.id} className="space-y-2 rounded-lg border bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between rounded-md bg-blue-50 p-3">
                {item.isEditing ? (
                  <form
                    className="flex w-full gap-2"
                    onSubmit={(e) => {
                      e.preventDefault();
                      const value = new FormData(e.currentTarget).get('q');
                      if (typeof value === 'string') void sendQuestion(value, item.id);
                    }}
                  >
                    <input name="q" type="text" defaultValue={item.question} className="w-full rounded border p-1 text-sm" />
                    <button type="submit" className="rounded bg-green-600 px-3 py-1 text-xs text-white">
                      Enregistrer
                    </button>
                    <button type="button" onClick={() => toggle(item.id, 'isEditing')} className="rounded bg-gray-400 px-2 py-1 text-xs text-white">
                      Annuler
                    </button>
                  </form>
                ) : (
                  <div className="flex w-full items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-blue-900">Vous : {item.question}</span>
                    <div className="flex shrink-0 gap-2 text-xs">
                      <button onClick={() => toggle(item.id, 'isEditing')} className="text-gray-500 underline hover:text-blue-600">
                        Modifier
                      </button>
                      <button onClick={() => toggle(item.id, 'isCollapsed')} className="text-gray-500 underline hover:text-gray-800">
                        {item.isCollapsed ? 'Déplier' : 'Réduire'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {!item.isCollapsed && item.error && (
                <div className="rounded-md border-l-4 border-red-500 bg-red-50 p-3 text-sm text-red-800">{item.error}</div>
              )}
              {!item.isCollapsed && item.result && (
                <div
                  className={`rounded-md border-l-4 p-3 text-sm leading-relaxed whitespace-pre-wrap text-gray-800 ${
                    item.result.refused ? 'border-amber-500 bg-amber-50' : 'border-emerald-500 bg-emerald-50'
                  }`}
                >
                  <p className="mb-1 font-semibold text-emerald-900">
                    {item.result.refused ? 'Hors du corpus' : 'Assistant RAG'} :
                  </p>
                  {item.result.answer}
                  <SourceList result={item.result} />
                  <Metrics result={item.result} />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="animate-pulse rounded-md bg-gray-100 p-3 text-sm text-gray-500">
              Recherche des réponses dans le document...
            </div>
          )}
          <div ref={chatEndRef} />
        </section>

        <form
          className="flex gap-2 pt-2"
          onSubmit={(e) => {
            e.preventDefault();
            void sendQuestion(inputQuestion);
          }}
        >
          <input
            type="text"
            value={inputQuestion}
            maxLength={500}
            onChange={(e) => setInputQuestion(e.target.value)}
            placeholder="Posez une question sur le contenu du PDF..."
            className="flex-1 rounded-lg border px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Envoyer
          </button>
        </form>
      </div>
    </div>
  );
}
