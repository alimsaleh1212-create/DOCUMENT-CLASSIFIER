# Licensing & Compliance

Summary of dataset and dependency licenses for the Document Classifier service.

## 📊 Dataset Licensing
### RVL-CDIP Dataset
- **License**: Academic / Research-Only
- **Usage**: Educational purposes for the Document Classification project.
- **Reference**: [CMU RVL-CDIP Repository](https://www.cs.cmu.edu/~aharley/rvl-cdip/)

---

## 💻 Core Stack Dependencies

| Category | Component | License |
|:---|:---|:---|
| **Language** | Python 3.11 | PSF |
| **Frameworks** | FastAPI, React 18, Vite | MIT |
| **Machine Learning** | PyTorch, torchvision | BSD-3-Clause |
| **Infrastructure** | Postgres 16, Redis 7, MinIO | LGPL/AGPL/Custom |
| **Security** | HashiCorp Vault, Casbin | BSL / Apache-2.0 |
| **Communication** | Paramiko, asyncpg, hvac | LGPL / MIT |

---

## 🛠 Component-Specific Licensing

### Member 1 — ML Artifacts
- **Model Weights**: ConvNeXt-Tiny (PyTorch/torchvision) - BSD-3-Clause.
- **Evaluation Logic**: Golden-set replay scripts - MIT.

### Member 2 — Frontend Assets
- **UI Stack**: React, TanStack Query, Tailwind CSS - MIT.
- **Iconography**: Lucide React - ISC.

### Member 3 — Pipeline & Infrastructure
- **Containerization**: `atmoz/sftp` - MIT.
- **Database Adapters**: SQLAlchemy, Alembic - MIT.
- **Object Storage**: MinIO Python SDK - Apache-2.0.

---

> [!TIP]
> Use `pip audit` and `pnpm licenses` to generate a full recursive dependency report before production deployment.