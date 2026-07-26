FROM python:3.11-slim AS base
RUN pip install --no-cache-dir poetry==2.4.1
WORKDIR /app
COPY services/ml-service/pyproject.toml services/ml-service/poetry.lock ./
COPY libs/common /libs/common
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root
COPY services/ml-service .
EXPOSE 8003
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
