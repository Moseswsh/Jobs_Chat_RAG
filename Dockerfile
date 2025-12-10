# Use lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file first and install dependencies, leverage cache to speed up build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy project code (including backend, data, frontend, etc.)
# Note: frontend directory also needs to be copied, as FastAPI will read index.html and static resources (CSS/JS) from this directory
COPY . .

# Expose port 8000 (Render will manage the port itself, this is just documentation)
EXPOSE 8000

# Start FastAPI application, keep consistent with local
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]



