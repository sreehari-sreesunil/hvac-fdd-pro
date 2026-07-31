FROM python:3.12-slim AS base
RUN pip install --no-cache-dir poetry==2.4.1
WORKDIR /app
COPY services/copilot-service/pyproject.toml services/copilot-service/poetry.lock* ./
COPY libs/common /libs/common
# Cache mount persists poetry's download cache across build attempts -
# chromadb/sentence-transformers (PyTorch) are large downloads, and a
# plain RUN layer discards all progress on any network failure, forcing
# a full redownload on every retry.
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root
COPY services/copilot-service .
EXPOSE 8005
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
