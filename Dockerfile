FROM python:3.12

WORKDIR /

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install --upgrade pip && pip install poetry
COPY bot-api relay-server poetry.lock pyproject.toml ./

RUN poetry install --no-root

CMD ["poetry", "run", "python", "bot-api"]