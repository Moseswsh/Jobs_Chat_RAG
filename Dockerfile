# Use lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file first and install dependencies, leverage cache to speed up build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only files needed by the application and its RAG corpus.
COPY backend ./backend
COPY frontend ./frontend
COPY data ./data

# Expose port 8000 (Render will manage the port itself, this is just documentation)
EXPOSE 8000

# Start FastAPI application, keep consistent with local
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"






