FROM python:3.11-slim AS base

RUN pip install --no-cache-dir poetry==2.4.1

WORKDIR /app

COPY services/telemetry-service/pyproject.toml services/telemetry-service/poetry.lock ./

COPY libs/common /libs/common

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY services/telemetry-service .

EXPOSE 8002

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
