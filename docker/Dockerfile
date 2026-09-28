# Cloud Run image for the FastAPI incident app (Day 9).
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY configs ./configs
COPY sql ./sql
COPY docs ./docs

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn datapilot.api.main:app --host 0.0.0.0 --port ${PORT}
