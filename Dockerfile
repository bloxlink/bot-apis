# FROM python:3.12

# ENV POETRY_VIRTUALENVS_CREATE true
# RUN pip install --upgrade pip && pip install poetry
# # COPY bot-api relay-server poetry.lock pyproject.toml ./
# COPY bot-api /app/bot-api/
# COPY relay-server /app/relay-server/
# COPY pyproject.toml poetry.lock /app/

# WORKDIR /app
# # RUN poetry install

# RUN poetry install --no-root

# CMD ["poetry", "run", "python", "bot-api"]

# `python-base` sets up all our shared environment variables
# FROM python:3.12.1-slim as python-base

#     # python
# ENV PYTHONUNBUFFERED=1 \
#     # prevents python creating .pyc files
#     PYTHONDONTWRITEBYTECODE=1 \
#     \
#     # pip
#     PIP_NO_CACHE_DIR=off \
#     PIP_DISABLE_PIP_VERSION_CHECK=on \
#     PIP_DEFAULT_TIMEOUT=100 \
#     \
#     # poetry
#     # https://python-poetry.org/docs/configuration/#using-environment-variables
#     POETRY_VERSION=1.0.3 \
#     # make poetry install to this location
#     POETRY_HOME="/opt/poetry" \
#     # make poetry create the virtual environment in the project's root
#     # it gets named `.venv`
#     POETRY_VIRTUALENVS_IN_PROJECT=true \
#     # do not ask any interactive question
#     POETRY_NO_INTERACTION=1 \
#     \
#     # paths
#     # this is where our requirements + virtual environment will live
#     PYSETUP_PATH="/opt/pysetup" \
#     VENV_PATH="/opt/pysetup/.venv"


# # prepend poetry and venv to path
# ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


# # `builder-base` stage is used to build deps + create our virtual environment
# FROM python-base as builder-base
# RUN apt-get update \
#     && apt-get install --no-install-recommends -y \
#         # deps for installing poetry
#         curl \
#         # deps for building python deps
#         build-essential

# # install poetry - respects $POETRY_VERSION & $POETRY_HOME
# RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

# # copy project requirement files here to ensure they will be cached.
# WORKDIR $PYSETUP_PATH
# COPY poetry.lock pyproject.toml ./

# # install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
# RUN poetry install --no-dev --no-root


# # `development` image is used during development / testing
# FROM python-base as development
# ENV FASTAPI_ENV=development
# WORKDIR $PYSETUP_PATH

# # copy in our built poetry + venv
# COPY --from=builder-base $POETRY_HOME $POETRY_HOME
# COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

# # quicker install as runtime deps are already installed
# RUN poetry install --no-root

# # will become mountpoint of our code
# WORKDIR /app

# EXPOSE 8000
# CMD ["poetry", "run", "python", "bot-api"]


# # `production` image used for runtime
# FROM python-base as production
# ENV FASTAPI_ENV=production
# COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
# COPY ./ /app/
# WORKDIR /app
# CMD ["poetry", "run", "python", "bot-api"]

FROM thehale/python-poetry:1.6.1-py3.12-slim
# ARG PROJECT_FOLDER_NAME
ENV PROJECT_ROOT_DIR=/workspaces/app

RUN apt update \
    && apt install git make --assume-yes --no-install-recommends

ENV PATH="$PROJECT_ROOT_DIR/.venv/bin:$PATH"

COPY bot-api $PROJECT_ROOT_DIR/bot-api/
COPY relay-server $PROJECT_ROOT_DIR/relay-server/
COPY pyproject.toml poetry.lock $PROJECT_ROOT_DIR/
WORKDIR $PROJECT_ROOT_DIR

RUN poetry install --no-root



CMD ["poetry", "run", "python", "bot-api"]