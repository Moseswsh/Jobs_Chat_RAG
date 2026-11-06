from pathlib import Path
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from backend.database import Base, engine, get_db
from backend.routers.conversations import router as conversations_router
from backend.rag import RAGPipeline
from backend.schemas import ChatRequest, ChatResponse
from backend.services.chat import respond_to_chat
from backend import models  # noqa: F401 - registers ORM models on Base.metadata


logger = logging.getLogger(__name__)


# Data directory (project root / data / steve_jobs)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "steve_jobs"

# Initialize FastAPI
app = FastAPI(title="Steve Jobs RAG Demo", version="0.1.0")
app.include_router(conversations_router)

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
    """Create the conversation tables and build the embeddings index."""
    try:
        Base.metadata.create_all(bind=engine)
        rag_pipeline.load_and_build_index()
        print(f"Index built, corpus dir: {DATA_DIR}")
    except Exception as exc:  # noqa: BLE001 - Fail fast on startup errors
        logger.error("Application startup failed (%s)", type(exc).__name__)
        raise


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Chat endpoint:
    1) Embed the question and retrieve relevant chunks.
    2) Use retrieved snippets as context for generation.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    return respond_to_chat(request, db=db, rag=rag_pipeline)


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

