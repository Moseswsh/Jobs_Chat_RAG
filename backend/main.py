from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from backend.rag import RAGPipeline


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    sources: List[str]


# Data directory (project root / data / steve_jobs)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "steve_jobs"

# Load .env (e.g., OPENAI_API_KEY), so we don't set env vars every time
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Steve Jobs RAG Demo", version="0.1.0")

# CORS: Allow browser frontend (even from different domains) to call this API on Render.
# In production, change "*" to the actual frontend domain (e.g., GitHub Pages).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files: serve CSS and JS files from the frontend directory
# Access /static/style.css and /static/main.js will read from the frontend directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")

# RAG pipeline; build once globally to avoid re-embedding
rag_pipeline = RAGPipeline(data_dir=DATA_DIR)


@app.on_event("startup")
def startup_event() -> None:
    """Build embeddings index on startup."""
    try:
        rag_pipeline.load_and_build_index()
        print(f"Index built, corpus dir: {DATA_DIR}")
    except Exception as exc:  # noqa: BLE001 - Fail fast on startup errors
        print(f"Startup failed: {exc}")
        raise


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint:
    1) Embed the question and retrieve relevant chunks.
    2) Use retrieved snippets as context for generation.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    try:
        docs = rag_pipeline.search(request.message)
        answer = rag_pipeline.generate_answer(request.message, docs)
        # Only return source filenames (deduplicated)
        source_files = list({doc.source for doc in docs})
        return ChatResponse(reply=answer, sources=source_files)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> str:
    """
    Root route: return the frontend chat page.
    Visiting https://jobs-rag-demo.onrender.com/ will display the chat interface.
    """
    index_path = BASE_DIR / "frontend" / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}

