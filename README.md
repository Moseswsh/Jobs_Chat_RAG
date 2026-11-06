# Jobs Chat RAG

A learning/demo chat application built with FastAPI, PostgreSQL, and OpenAI. It retrieves passages from the text files in `data/steve_jobs`, keeps separate conversation histories, and uses recent turns to understand follow-up questions.

## Features

- Builds the existing in-memory RAG index from `.txt` files in `data/steve_jobs` at startup.
- Stores conversations and messages in PostgreSQL.
- Creates UUID-based conversations, lists only the current browser's saved conversations, restores a selected conversation after refresh, and supports deleting a conversation.
- Uses up to eight recent messages by default for answer context. Recent user questions are also combined with the current question for retrieval, helping resolve follow-ups such as “Why did he say that?”
- Returns retrieved source filenames with each answer.
- Provides a browser chat UI, `/docs` API documentation, and a `/health` endpoint.

The project has no account system. Conversation IDs are unguessable UUIDs, not user authentication. The browser stores its conversation ID list in `localStorage`; clearing browser data or switching browsers loses that list. Do not use this demo for sensitive conversations or as a public multi-user service without adding authentication and access controls.

## Run with Docker Compose

Requirements: Docker Desktop with Docker Compose and an OpenAI API key that can access the configured embedding and chat models.

1. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell, run `Copy-Item .env.example .env`. Set `OPENAI_API_KEY` in `.env`. Compose supplies the internal PostgreSQL URL to the app container. Never commit this file or real credentials.

2. Build and start the app and PostgreSQL:

   ```bash
   docker compose up --build
   ```

   Compose waits for PostgreSQL's health check before starting FastAPI. On startup, SQLAlchemy creates the `conversations` and `messages` tables, then builds the RAG index. Open <http://localhost:8000> for the chat UI or <http://localhost:8000/docs> for API documentation.

   Stop the containers with `Ctrl+C`, or run `docker compose down` in another terminal. PostgreSQL data is kept in the `postgres_data` named volume. To delete the database data too, use `docker compose down --volumes`.

The PostgreSQL credentials in `compose.yaml` are for local development only. Change them before using this configuration in a shared or public environment. The database port is published only on localhost.

## API

### `POST /conversations`

Creates a conversation and returns its UUID, title, and timestamps. The application intentionally has no endpoint that lists all database conversations.

### `GET /conversations/{conversation_id}/messages`

Returns messages in chronological order. Returns 404 when the conversation does not exist.

### `DELETE /conversations/{conversation_id}`

Deletes the conversation and its associated messages. Returns 404 when it does not exist.

### `POST /chat`

Request:

```json
{
  "conversation_id": "replace-with-a-conversation-uuid",
  "message": "What did Steve Jobs say about design?"
}
```

Response:

```json
{
  "conversation_id": "replace-with-a-conversation-uuid",
  "title": "What did Steve Jobs say about design?",
  "reply": "...",
  "sources": ["stanford_2005.txt"]
}
```

A blank message returns HTTP 400. An unknown conversation returns HTTP 404. If retrieval or model generation fails, the user message remains stored for continuity, and no assistant reply is saved.

### `GET /health`

Returns `{"status":"ok"}`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `DATABASE_URL` | — | PostgreSQL connection URL; required |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `GENERATION_MODEL` | `gpt-4.1-mini` | Chat completion model |
| `CHUNK_SIZE` | `200` | Words per corpus chunk |
| `CHUNK_OVERLAP` | `40` | Overlapping words between chunks |
| `TOP_K` | `4` | Number of retrieved chunks |
| `CONVERSATION_HISTORY_MESSAGES` | `8` | Maximum prior messages sent as conversation context; clamped to 2–20 |

## Deployment

The repository includes a Dockerfile and a Render Blueprint example. Set both `OPENAI_API_KEY` and `DATABASE_URL` in the deployment environment. For production, use a managed PostgreSQL database and a private credential. Tables are created with SQLAlchemy `create_all`; schema migrations are not included in this first upgrade.

## Notes

The assistant is an AI persona inspired by public source material, not Steve Jobs. Answers may be inaccurate. The application includes prompt guidance for private-life and post-2011 questions, but it is not a fact-checking system.
