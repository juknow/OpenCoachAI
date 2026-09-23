FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

COPY requirements.txt requirements-whisper.txt ./
RUN pip install --no-cache-dir -r requirements-whisper.txt

COPY app ./app

RUN useradd --create-home --uid 10001 appuser \
    && install -d -o appuser -g appuser /home/appuser/.cache/huggingface
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
