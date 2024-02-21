FROM python:3.12

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install --upgrade pip && pip install poetry
COPY bot-api poetry.lock pyproject.toml /app/

WORKDIR /app
RUN poetry install

CMD ["poetry", "run", "python", "bot-api"]