# Build stage for React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Final stage for Python FastAPI backend
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY docs/ ./docs/
COPY data/ ./data/
COPY experiments/ ./experiments/

# Copy built frontend assets
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Initialize models if needed and start server
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]

