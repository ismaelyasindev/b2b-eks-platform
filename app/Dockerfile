FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /workspace

RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip setuptools wheel

COPY --chown=10001:10001 . ./app

ENV PYTHONPATH=/workspace

EXPOSE 8000

USER 10001:10001
