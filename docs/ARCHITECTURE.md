# Architecture Notes

## Overview

This document explains how the Misinformation Risk Assessment System is structured as a full-stack inference application.

At a high level, the system combines:

- a React frontend for interactive claim submission
- a .NET 8 orchestration layer
- a Python classical ML scorer
- a FastAPI transformer service
- EF Core persistence

The design goal is not just to produce a label, but to demonstrate an explainable end-to-end ML product workflow.

## Core Architectural Principle

The backend is the orchestration boundary.

It is responsible for:

- validating incoming requests
- extracting heuristic feature signals
- invoking the classical ML scoring process
- invoking the transformer service
- combining the outputs into a single risk score
- producing explainability fields
- persisting the final analysis result

That means the frontend stays thin, while model composition and business logic remain centralized in the API layer.

## Component Responsibilities

### Frontend

The frontend is a Vite-based React SPA.

Primary responsibilities:

- collect `title`, `content`, and `source`
- submit requests to the backend API
- render risk level, confidence score, explanation, and explainability fields
- show result history and result-detail pages

The frontend does not call Python services directly.

### Backend API

The ASP.NET Core API is the central coordinator.

Primary responsibilities:

- expose `/api/analyze`, `/api/health`, `/api/history`, and `/api/result/{id}`
- extract feature engineering signals before model fusion
- call the classical Python predictor through a process boundary
- call the FastAPI BERT service over HTTP
- compute hybrid scoring and explanation text
- persist analysis records through EF Core

The backend uses:

- Azure SQL when a connection string is provided
- in-memory persistence for local development when no SQL connection string is configured

### Classical ML Layer

The classical ML stack lives under `backend/Services/Ml/`.

It consists of:

- TF-IDF vectorization
- Logistic Regression
- Random Forest
- a Python training script
- a Python scoring script
- serialized artifacts stored under `backend/Services/Ml/artifacts/`

Why keep this as a separate Python execution path:

- it preserves the original scikit-learn artifact workflow
- it keeps model training and scoring straightforward
- it demonstrates polyglot orchestration from a .NET backend

### Transformer Service

The transformer layer runs as a separate FastAPI service.

Primary responsibilities:

- load a DistilBERT sequence-classification checkpoint
- expose `/health`
- expose `/predict`
- return a transformer score and salient tokens

This separation keeps transformer dependencies isolated from the .NET runtime and makes the architecture easier to evolve toward service-based deployment.

### Persistence Layer

Persistence is handled through EF Core.

The stored record includes:

- raw request fields
- final risk label
- confidence score
- explanation text
- serialized feature signals
- timestamp

This supports:

- history views
- result recall by id
- future auditing or analytics work

## End-to-End Request Flow

1. A user submits a claim from the React frontend.
2. The backend validates the request contract.
3. Feature engineering extracts numeric heuristic signals from `title`, `content`, and `source`.
4. The backend sends the request to the classical Python scorer.
5. The backend sends the request to the FastAPI transformer service.
6. The hybrid scoring layer computes the final weighted result.
7. The backend adds explanation text and model score breakdowns.
8. The result is persisted through EF Core.
9. The response is returned to the frontend.

## Hybrid Scoring Model

The current base fusion formula is:

```text
0.5 * Logistic Regression
+ 0.3 * Random Forest
+ 0.2 * DistilBERT
```

This weighted combination is then adjusted by small interpretable heuristics for factors such as:

- missing source
- emotional wording
- uppercase emphasis
- exclamation count
- exaggeration cues
- limited context
- source trust patterns

This design intentionally blends:

- statistical lexical signals
- tree-based nonlinear signals
- transformer semantic signals
- lightweight human-readable adjustments

## Explainability Design

The explainability payload is exposed through `featureSignals`.

It includes:

- handcrafted feature signals
- top keywords from the classical pipeline
- salient transformer tokens
- per-model scores

The architecture goal is practical explainability, not academic interpretability purity.

That means the system focuses on signals that are easy to understand in a product demo:

- why the score moved upward
- which lexical terms mattered
- which transformer tokens stood out
- how the model branches contributed numerically

## Local Development Model

The repository supports local development across:

- Windows PowerShell
- macOS/Linux shells

The recommended local flow is:

1. create `.env`
2. install Python dependencies
3. install frontend dependencies
4. prepare the LIAR dataset
5. train classical artifacts
6. prepare a local DistilBERT checkpoint
7. start `bert_service`
8. start backend
9. start frontend

The repository also includes helper scripts:

- `scripts/train_all.sh`
- `scripts/train_all.ps1`
- `scripts/dev_start.sh`
- `scripts/dev_start.ps1`

## Deployment Shape

The architecture is already aligned with a cloud-friendly split:

- frontend as a static app
- backend as an App Service or containerized API
- transformer service as a separate HTTP service
- SQL persistence as Azure SQL

This makes the project suitable for both:

- local demo workflows
- portfolio discussion around productionization paths

## Why This Project Works as a Portfolio Piece

This system demonstrates:

- full-stack product thinking
- service orchestration across multiple runtimes
- practical ML engineering
- model explainability in a user-facing workflow
- API and persistence design
- local-to-cloud architectural continuity

It is stronger than a notebook-only ML demo because the models are embedded inside an actual application stack.
