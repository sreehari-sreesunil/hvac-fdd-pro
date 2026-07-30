FROM python:3.12-slim AS base
RUN pip install --no-cache-dir poetry==2.4.1
WORKDIR /app
COPY services/ml-service/pyproject.toml services/ml-service/poetry.lock ./
COPY libs/common /libs/common
# Cache mount persists poetry's download cache ACROSS build attempts,
# even failed ones - on a slow/unreliable connection, a retry only
# needs to fetch what's genuinely missing, not redownload everything
# from scratch (a plain RUN layer discards all progress on failure).
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root
COPY services/ml-service .
EXPOSE 8003
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
