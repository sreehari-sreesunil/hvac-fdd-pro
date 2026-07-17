FROM python:3.11-slim AS base

# Install Poetry
RUN pip install --no-cache-dir poetry==2.4.1

WORKDIR /app

# Copy only dependency files first — this is a deliberate layer-caching trick:
# Docker only re-runs `poetry install` when pyproject.toml/poetry.lock change,
# not on every code edit, which makes rebuilds dramatically faster.
COPY services/asset-service/pyproject.toml services/asset-service/poetry.lock ./

# Poetry needs the local `common` dependency's pyproject.toml to resolve too
COPY libs/common /libs/common

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY services/asset-service .

EXPOSE 8001

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
