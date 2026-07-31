FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY backend/MisinformationRiskAssessment.Api.csproj backend/
RUN dotnet restore backend/MisinformationRiskAssessment.Api.csproj

COPY backend/ backend/
RUN dotnet publish backend/MisinformationRiskAssessment.Api.csproj -c Release -o /app/publish /p:UseAppHost=false

# The .joblib artifacts are too large for git, so they are published as a release
# bundle and baked in here. Leave ARTIFACT_RELEASE_TAG empty for local development,
# where docker-compose mounts ./backend/Services/Ml/artifacts instead.
FROM python:3.11-slim AS artifacts

ARG ARTIFACT_REPO=HarlanAlternative/MisinformationRiskAssessmentSystem
ARG ARTIFACT_RELEASE_TAG=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /staged
COPY scripts/verify_bundle.py /tmp/verify_bundle.py

RUN mkdir -p classical \
    && if [ -n "$ARTIFACT_RELEASE_TAG" ]; then \
         echo "Fetching classical-artifacts bundle from release ${ARTIFACT_RELEASE_TAG}" \
         && curl -fsSL --retry 3 -o bundle.tar.gz \
              "https://github.com/${ARTIFACT_REPO}/releases/download/${ARTIFACT_RELEASE_TAG}/classical-artifacts.tar.gz" \
         && tar -xzf bundle.tar.gz -C classical \
         && rm bundle.tar.gz \
         && python /tmp/verify_bundle.py classical; \
       else \
         echo "ARTIFACT_RELEASE_TAG not set: building without baked artifacts."; \
       fi

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=build /app/publish ./
COPY backend/Services/Ml /app/Services/Ml

RUN python3 -m venv /opt/backend-venv \
    && /opt/backend-venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/backend-venv/bin/python -m pip install --no-cache-dir -r /app/Services/Ml/requirements.txt \
    && mkdir -p /app/Services/Ml/artifacts /app/logs

COPY --from=artifacts /staged/classical /app/Services/Ml/artifacts

ENV PATH=/opt/backend-venv/bin:${PATH}
ENV ASPNETCORE_URLS=http://+:5000
ENV BertService__Url=http://bert_service:8001
ENV MachineLearning__PythonExecutable=/opt/backend-venv/bin/python

EXPOSE 5000

ENTRYPOINT ["dotnet", "MisinformationRiskAssessment.Api.dll"]
