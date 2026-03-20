FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV BERT_MODEL_DIR=/app/models/distilbert-liar
ENV BERT_MAX_LENGTH=256
ENV HF_HOME=/app/.cache/huggingface

COPY bert_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/models /app/.cache/huggingface

COPY bert_service/ ./

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
