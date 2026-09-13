import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

interface Message {
  id: string;
  question: string;
  answer: string;
  isCollapsed: boolean;
  isEditing: boolean;
}

const BACKEND_URL = "http://localhost:8000";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [inputQuestion, setInputQuestion] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUploadWithProgress = async () => {
    if (!file) return;

    setIsUploading(true);
    setProgress(0);
    setUploadStatus("Envoi du fichier au serveur...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${BACKEND_URL}/upload-stream`, {
        method: "POST",
        body: formData,
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.replace("data: ", ""));
            if (data.progress !== undefined) {
              setProgress(data.progress);
              setUploadStatus(data.message);
            }
            if (data.error) {
              setUploadStatus(`Erreur : ${data.error}`);
            }
          }
        }
      }
    } catch (err) {
      setUploadStatus("Erreur lors de l'indexation du document.");
    } finally {
      setIsUploading(false);
    }
  };

  const sendQuestion = async (questionText: string, messageIdToReplace?: string) => {
    if (!questionText.trim()) return;
    setLoading(true);

    try {
      const res = await axios.post(`${BACKEND_URL}/chat`, { question: questionText });
      const newAnswer = res.data.answer;

      if (messageIdToReplace) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageIdToReplace
              ? { ...m, question: questionText, answer: newAnswer, isEditing: false, isCollapsed: false }
              : m
          )
        );
      } else {
        setMessages((prev) => [
          ...prev.map((m) => ({ ...m, isCollapsed: true })),
          {
            id: Date.now().toString(),
            question: questionText,
            answer: newAnswer,
            isCollapsed: false,
            isEditing: false,
          },
        ]);
        setInputQuestion('');
      }
    } catch (err) {
      alert("Erreur de communication avec le serveur.");
    } finally {
      setLoading(false);
    }
  };

  const toggleCollapse = (id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, isCollapsed: !m.isCollapsed } : m))
    );
  };

  const toggleEdit = (id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, isEditing: !m.isEditing } : m))
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-6 font-sans">
      <div className="w-full max-w-3xl bg-white rounded-xl shadow-md p-6 space-y-6">
        <h1 className="text-2xl font-bold text-center text-gray-800">
          RAG Knowledge Assistant
        </h1>

        {/* Importation PDF avec Barre de Progression */}
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center bg-gray-50">
          <h2 className="font-semibold text-gray-700 mb-2">1. Importer un Document PDF</h2>
          <div className="flex items-center justify-center space-x-3 mb-3">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={isUploading}
              className="text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <button
              onClick={handleUploadWithProgress}
              disabled={isUploading || !file}
              className="bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-800 text-sm font-medium disabled:opacity-50"
            >
              Charger le PDF
            </button>
          </div>

          {/* Barre de Progression Visualisée */}
          {isUploading && (
            <div className="w-full space-y-1">
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-blue-600 h-3 transition-all duration-200 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="text-xs text-blue-600 font-bold text-right">{progress}%</div>
            </div>
          )}

          {uploadStatus && (
            <p className="mt-2 text-xs text-blue-800 font-medium">{uploadStatus}</p>
          )}
        </div>

        {/* Historique du Chat */}
        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
          {messages.map((item) => (
            <div key={item.id} className="border rounded-lg p-4 bg-white shadow-sm space-y-2">
              <div className="flex justify-between items-start bg-blue-50 p-3 rounded-md">
                {item.isEditing ? (
                  <div className="w-full flex space-x-2">
                    <input
                      type="text"
                      defaultValue={item.question}
                      id={`edit-input-${item.id}`}
                      className="w-full border rounded p-1 text-sm"
                    />
                    <button
                      onClick={() => {
                        const inputEl = document.getElementById(`edit-input-${item.id}`) as HTMLInputElement;
                        if (inputEl) sendQuestion(inputEl.value, item.id);
                      }}
                      className="bg-green-600 text-white px-3 py-1 rounded text-xs"
                    >
                      Enregistrer
                    </button>
                    <button
                      onClick={() => toggleEdit(item.id)}
                      className="bg-gray-400 text-white px-2 py-1 rounded text-xs"
                    >
                      Annuler
                    </button>
                  </div>
                ) : (
                  <div className="flex justify-between w-full items-center">
                    <span className="font-semibold text-blue-900 text-sm">Vous : {item.question}</span>
                    <div className="flex space-x-2 text-xs">
                      <button
                        onClick={() => toggleEdit(item.id)}
                        className="text-gray-500 hover:text-blue-600 underline"
                      >
                        Modifier
                      </button>
                      <button
                        onClick={() => toggleCollapse(item.id)}
                        className="text-gray-500 hover:text-gray-800 underline"
                      >
                        {item.isCollapsed ? "Déplier" : "Réduire"}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {!item.isCollapsed && (
                <div className="bg-emerald-50 p-3 rounded-md border-l-4 border-emerald-500 text-gray-800 text-sm whitespace-pre-wrap leading-relaxed">
                  <p className="font-semibold text-emerald-900 mb-1">Assistant RAG :</p>
                  {item.answer}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="p-3 bg-gray-100 text-gray-500 text-sm rounded-md animate-pulse">
              Recherche des réponses dans le document...
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Question */}
        <div className="flex space-x-2 pt-2">
          <input
            type="text"
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendQuestion(inputQuestion)}
            placeholder="Posez une question sur le contenu du PDF..."
            className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => sendQuestion(inputQuestion)}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Envoyer
          </button>
        </div>
      </div>
    </div>
  );
}