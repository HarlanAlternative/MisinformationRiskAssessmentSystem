# The fine-tuned checkpoint is far too large for git, so it is published as a
# release bundle and baked in here. Leave ARTIFACT_RELEASE_TAG empty for local
# development, where docker-compose mounts ./bert_service/models instead.
FROM python:3.11-slim AS artifacts

ARG ARTIFACT_REPO=HarlanAlternative/MisinformationRiskAssessmentSystem
ARG ARTIFACT_RELEASE_TAG=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /staged
COPY scripts/verify_bundle.py /tmp/verify_bundle.py

RUN mkdir -p distilbert-liar \
    && if [ -n "$ARTIFACT_RELEASE_TAG" ]; then \
         echo "Fetching distilbert-liar bundle from release ${ARTIFACT_RELEASE_TAG}" \
         && curl -fsSL --retry 3 -o bundle.tar.gz \
              "https://github.com/${ARTIFACT_REPO}/releases/download/${ARTIFACT_RELEASE_TAG}/distilbert-liar.tar.gz" \
         && tar -xzf bundle.tar.gz -C distilbert-liar \
         && rm bundle.tar.gz \
         && python /tmp/verify_bundle.py distilbert-liar; \
       else \
         echo "ARTIFACT_RELEASE_TAG not set: building without a baked checkpoint."; \
       fi

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV BERT_MODEL_DIR=/app/models/distilbert-liar
ENV BERT_MAX_LENGTH=256
ENV HF_HOME=/app/.cache/huggingface

COPY bert_service/requirements.txt ./
# Installing torch from default PyPI drags in ~2.5 GB of CUDA libraries that a
# CPU-only inference service never loads. Pin the CPU wheel first, matching the
# 2.5.1+cpu the development environment runs; the requirements install then finds
# torch already satisfied.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/models /app/.cache/huggingface

COPY bert_service/ ./
COPY --from=artifacts /staged/distilbert-liar /app/models/distilbert-liar

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
