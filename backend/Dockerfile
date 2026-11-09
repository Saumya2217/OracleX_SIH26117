ARG PYTHON_BASE_IMAGE=python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84
FROM ${PYTHON_BASE_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=.

COPY requirements.lock /tmp/requirements.lock
COPY wheelhouse /tmp/wheelhouse
RUN python -m pip install --no-cache-dir --no-index --find-links=/tmp/wheelhouse \
      --require-hashes -r /tmp/requirements.lock \
    && rm -rf /tmp/wheelhouse /tmp/requirements.lock

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
