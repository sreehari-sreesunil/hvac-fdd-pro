FROM python:3.11-slim AS base
RUN pip install --no-cache-dir poetry==2.4.1
WORKDIR /app
COPY services/notification-service/pyproject.toml services/notification-service/poetry.lock* ./
COPY libs/common /libs/common
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root
COPY services/notification-service .
EXPOSE 8004
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
