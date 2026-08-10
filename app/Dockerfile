# Official Python image via AWS Public ECR (no Docker Hub login required).
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONPATH=/workspace

EXPOSE 8000
