# Jobs Chat RAG

A small retrieval-augmented chat application built with FastAPI, OpenAI, and a static browser UI. It retrieves passages from the text files in `data/steve_jobs` and uses them to answer questions in a Steve Jobs-inspired persona for learning and demonstration.

## Features

- Loads every non-empty `.txt` file directly inside `data/steve_jobs` at application startup.
- Splits corpus text into overlapping word-based chunks and creates embeddings with OpenAI.
- Retrieves the most relevant chunks using cosine similarity, then generates an answer with the retrieved context.
- Returns the source filenames alongside each answer.
- Serves the chat page, JavaScript, and CSS from the FastAPI application.
- Includes `/health` for a basic service health check.

The corpus is indexed in memory when the application starts. Restart the application after changing corpus files so the index is rebuilt.

## Requirements

- Python 3.11 or newer
- An OpenAI API key with access to the configured embedding and chat models

## Run locally

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set `OPENAI_API_KEY` in the environment or in a root `.env` file:

   ```text
   OPENAI_API_KEY=your_api_key
   ```

4. Start the server:

   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

5. Open <http://localhost:8000> in a browser. The API documentation is available at <http://localhost:8000/docs>.

## API

### `POST /chat`

Request:

```json
{"message": "What did Steve Jobs say about design?"}
```

Response:

```json
{"reply": "...", "sources": ["stanford_2005.txt"]}
```

An empty message returns HTTP 400. Retrieval or model errors return HTTP 500.

### `GET /health`

Returns:

```json
{"status": "ok"}
```

## Configuration

The following environment variables are supported:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | API key used for embeddings and chat completions |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `GENERATION_MODEL` | `gpt-4.1-mini` | Chat completion model |
| `CHUNK_SIZE` | `200` | Words per corpus chunk |
| `CHUNK_OVERLAP` | `40` | Overlapping words between chunks |
| `TOP_K` | `4` | Number of retrieved chunks |

## Deployment

The repository includes a Dockerfile and a Render Blueprint example. Configure `OPENAI_API_KEY` in the deployment environment; do not commit secrets. The frontend and API are served from the same origin by default.

## Notes

This is a learning/demo project. It generates AI-written responses inspired by public source material; answers may be inaccurate and do not represent Steve Jobs. The application includes basic prompt guidance for private-life and post-2011 questions, but it is not a fact-checking system.
