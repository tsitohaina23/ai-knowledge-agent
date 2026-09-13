# 📚 RAG Knowledge Assistant (Local Setup)

Application web RAG (Retrieval-Augmented Generation) permettant d'interroger le contenu de documents PDF techniques grâce à des Embeddings locaux et au LLM Ultra-rapide via Groq.

---

## 🚀 Architecture Technique

* **Backend :** FastAPI (Python)
* **Vector Store :** ChromaDB (Stockage vectoriel local)
* **Embeddings :** FastEmbed (Génération locale d'embeddings)
* **LLM :** Groq API (`openai/gpt-oss-120b` ou `llama-3.1-8b-instant`)
* **Frontend :** React + TypeScript (Vite + Tailwind CSS)

---

## 🛠️ Installation & Configuration

### 1. Prérequis
* Python 3.10+
* Node.js 18+

### 2. Clé API Groq
Créez un fichier `.ven` à la racine du dossier `backend/` avec votre clé API :
```env
GROQ_API_KEY=votre_cle_api_groq_ici