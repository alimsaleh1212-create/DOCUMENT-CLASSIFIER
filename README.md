# Document Classifier Service

An end-to-end authenticated service for automatic document layout classification using fine-tuned ConvNeXt-Tiny models.

## 📋 System Overview
The service automates the classification of 16 document layout categories (invoices, resumes, letters, etc.). It handles the full lifecycle:
1. **Ingestion**: Polls SFTP for TIFF images and moves them to secure object storage.
2. **Classification**: Asynchronous inference using a fine-tuned Vision Transformer (ConvNeXt).
3. **Review**: Authenticated UI for browsing predictions, inspecting overlays, and manual relabeling.

---

## 🛠 Technology Stack

### Backend
- **Core**: Python 3.11, FastAPI
- **Auth**: `fastapi-users`, Casbin (RBAC), HashiCorp Vault
- **Data**: SQLAlchemy 2.0 (Async), Alembic, PostgreSQL 16
- **Tasks**: RQ (Redis Queue), Redis 7

### Machine Learning
- **Backbone**: `convnext_tiny`
- **Training**: Google Colab ([Training Notebook](https://colab.research.google.com/drive/14s1vsg8iVFfOQJxnOE5K4mwymwITiXSM?usp=sharing))
- **Validation**: Golden-set replay with SHA-256 integrity checks.

### Frontend
- **Framework**: React 18, TypeScript, Vite
- **State**: TanStack Query v5, React Router v6
- **Styling**: Tailwind CSS

---

## 👥 Team & Responsibilities

| Member | Focus Area | Key Components |
|:---|:---|:---|
| **Member 1** | ML & Inference | Model fine-tuning, `predictor.py`, `worker/` logic. |
| **Member 2** | API & Frontend | FastAPI routers, Services, Auth, React UI. |
| **Member 3** | Data & Infrastructure | DB Schema, SFTP Ingest, Docker-Compose, CI/CD. |

---

## 🚀 Quick Start

1. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Set VAULT_TOKEN in .env
   ```

2. **Launch Stack**:
   ```bash
   docker compose up -d
   ./docker/vault-init.sh  # Seed secrets
   ```

3. **Access Services**:
   - **Frontend**: [http://localhost:5173](http://localhost:5173)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **MinIO**: [http://localhost:9001](http://localhost:9001)

---

## 📖 Extended Documentation
- [DECISIONS.md](./DECISIONS.md) — Architecture & design rationale.
- [RUNBOOK.md](./RUNBOOK.md) — Operations, recovery, and maintenance.
- [LICENSES.md](./LICENSES.md) — Dependency and dataset licensing.
- [ARCH.md](./ARCH.md) — Detailed technical architecture and folder layout.