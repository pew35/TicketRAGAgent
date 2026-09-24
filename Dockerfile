FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server

WORKDIR /app
COPY server/requirements-cloud.txt ./server/requirements-cloud.txt
RUN pip install --no-cache-dir -r server/requirements-cloud.txt

COPY server/ ./server/
COPY agent/data/ ./agent/data/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist/

WORKDIR /app/server
CMD ["sh", "-c", "alembic upgrade head && uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
