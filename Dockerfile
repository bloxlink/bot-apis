FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install --upgrade pip && pip install poetry
COPY bot-api /app/bot-api

WORKDIR /app/bot-api
RUN poetry install

CMD ["poetry", "run", "python", "bot-api"]