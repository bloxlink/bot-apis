FROM python:3.12

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install --upgrade pip && pip install poetry
# COPY bot-api relay-server poetry.lock pyproject.toml ./
COPY bot-api /app/bot-api/
COPY relay-server /app/relay-server/
COPY pyproject.toml poetry.lock /app/

WORKDIR /app
# RUN poetry install

RUN poetry install --no-root

CMD ["poetry", "run", "python", "bot-api"]