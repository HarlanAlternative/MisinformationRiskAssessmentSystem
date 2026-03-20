FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY backend/MisinformationRiskAssessment.Api.csproj backend/
RUN dotnet restore backend/MisinformationRiskAssessment.Api.csproj

COPY backend/ backend/
RUN dotnet publish backend/MisinformationRiskAssessment.Api.csproj -c Release -o /app/publish /p:UseAppHost=false

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

ENV PATH=/opt/backend-venv/bin:${PATH}
ENV ASPNETCORE_URLS=http://+:5000
ENV BertService__Url=http://bert_service:8001
ENV MachineLearning__PythonExecutable=/opt/backend-venv/bin/python

EXPOSE 5000

ENTRYPOINT ["dotnet", "MisinformationRiskAssessment.Api.dll"]
