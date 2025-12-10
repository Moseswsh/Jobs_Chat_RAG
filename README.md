<<<<<<< HEAD
# Steve Jobs RAG Demo

Simple RAG demo based on Steve Jobs public talks/interviews (pre-2011) with FastAPI + OpenAI + a minimal vanilla JS frontend.

## Backend (FastAPI)
1) (Recommended) create venv  
   - `python -m venv .venv`  
   - Windows: `.\.venv\Scripts\activate` ; macOS/Linux: `source .venv/bin/activate`
2) Install deps  
   - `pip install -r requirements.txt`
3) Env vars (use `.env` in project root)  
   - `OPENAI_API_KEY=your_key`  
   - Optional: `EMBEDDING_MODEL`, `GENERATION_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`
4) Run  
   - `uvicorn backend.main:app --reload --port 8000`

## Frontend
- Option 1: Open `frontend/index.html` with VSCode Live Server  
- Option 2: `python -m http.server 5500` in project root, then visit `http://localhost:5500/frontend/index.html`

## Notes
- API: `POST /chat` body `{"message":"..."}` returns `{"reply":"...","sources":[...]}` (sources list filenames only).  
- Corpus: `data/steve_jobs/`; indexed on startup.  
- For learning/demo only; answers do not represent the real person and may contain errors. Post-2011 topics are treated as hypothetical.

## Deploy to Render (Backend)
- Prereqs: Render account linked to GitHub; repo contains `Dockerfile` (and optional `render.yaml`); set `OPENAI_API_KEY` in Render console (do not commit real keys).
- Steps:
  1) Log in to Render, create a new Web Service.
  2) Connect the GitHub repo containing this project.
  3) Render detects the root `Dockerfile`; use default build settings (or adjust).
  4) In "Environment" tab, set `OPENAI_API_KEY`.
  5) Deploy and wait until status is "Live".
  6) Service URL will look like `https://your-service-name.onrender.com`.
  7) Test endpoints: `GET /health`, `POST /chat` with `{"message": "Hello"}`.
- Frontend: host `frontend/` locally or via GitHub Pages; set `API_BASE_URL` in `frontend/main.js` to your Render URL so it calls the deployed backend.


=======
# Jobs_Chat_RAG
In this project, RAG-powered “Steve Jobs” persona chatbot built with FastAPI and OpenAI. Retrieves answers from his real speeches/interviews and runs as a full-stack demo (API + minimal web UI).
>>>>>>> 25ee0f4c7a0c2c787c6a67ecb6debe83e38e3554
