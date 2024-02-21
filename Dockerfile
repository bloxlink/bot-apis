FROM python:3.12 as builder

RUN pip install poetry==1.4.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY bot-api/ /app/bot-api
COPY relay-server/ /app/relay-server

RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev

# ENV VIRTUAL_ENV=/app/.venv \
#     PATH="/app/.venv/bin:$PATH"

# COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

ENTRYPOINT ["poetry", "run", "python", "bot-api"]