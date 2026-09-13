import os
import json
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=".ven")

app = FastAPI(title="RAG AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embeddings = FastEmbedEmbeddings()
PERSIST_DIRECTORY = "./chroma_db"
vector_db = None

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

class QueryRequest(BaseModel):
    question: str

@app.post("/upload-stream")
async def upload_pdf_stream(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être au format PDF.")

    temp_path = f"./{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    async def generate_progress():
        global vector_db
        try:
            yield f"data: {json.dumps({'progress': 5, 'message': 'Lecture du PDF...'})}\n\n"
            await asyncio.sleep(0.1)

            loader = PyPDFLoader(temp_path)
            docs = loader.load()

            yield f"data: {json.dumps({'progress': 20, 'message': 'Découpage du texte en blocs...'})}\n\n"
            await asyncio.sleep(0.1)

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = text_splitter.split_documents(docs)
            total_chunks = len(chunks)

            # Traitement par lots (batchs) pour envoyer la progression
            batch_size = 20
            vector_db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)

            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i + batch_size]
                vector_db.add_documents(batch)
                
                # Calcul du pourcentage (de 20% à 95%)
                percent = int(20 + ((i + len(batch)) / total_chunks) * 75)
                yield f"data: {json.dumps({'progress': percent, 'message': f'Indexation : {i + len(batch)}/{total_chunks} blocs'})}\n\n"
                await asyncio.sleep(0.01)

            vector_db.persist()
            if os.path.exists(temp_path):
                os.remove(temp_path)

            yield f"data: {json.dumps({'progress': 100, 'message': f'PDF de {len(docs)} pages ingéré avec succès !'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate_progress(), media_type="text/event-stream")

@app.post("/chat")
async def chat(request: QueryRequest):
    global vector_db
    if not vector_db:
        if os.path.exists(PERSIST_DIRECTORY):
            vector_db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
        else:
            raise HTTPException(status_code=400, detail="Veuillez charger un fichier PDF au préalable.")
    
    results = vector_db.similarity_search(request.question, k=5)
    cleaned_chunks = [doc.page_content.replace("\n", " ").strip() for doc in results]
    context = "\n\n".join(cleaned_chunks)

    if not groq_client:
        return {"answer": "[ERREUR] Clé GROQ_API_KEY non trouvée."}

    try:
        prompt = f"""Tu es un assistant IA fluide et direct. 
Consignes de réponse :
1. N'utilise JAMAIS d'astérisques (pas de **, pas de *).
2. Ne commence JAMAIS par des mots comme "Réponse:", "Conclusion:", "Voici la réponse:".
3. Réponds directement, clairement et en français naturel en t'appuyant uniquement sur le contexte suivant.

Contexte:
{context}

Question de l'utilisateur: {request.question}"""

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        clean_answer = response.choices[0].message.content.replace("**", "").replace("*", "")
        return {"answer": clean_answer}

    except Exception as e:
        return {"answer": f"Erreur lors de la génération par l'IA : {str(e)}"}