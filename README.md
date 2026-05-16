# ShipSage 🚀

> **From repo to production-ready infrastructure — in seconds.**

AI-powered DevOps pipeline generator that analyzes any public GitHub repository and generates production-ready Dockerfile, docker-compose, Kubernetes manifests, CI/CD pipelines, AWS Terraform, ELK monitoring stack, and environment configs.

Built for the **IBM Bob Hackathon 2026** · Powered by **IBM watsonx Granite**

---

## 🎯 The Problem

Developers spend **2-3 days** writing DevOps boilerplate for every new project — Dockerfiles, K8s manifests, CI/CD pipelines, AWS infrastructure. It's repetitive, error-prone, and keeps engineers away from building actual features.

**ShipSage automates this entire process in 30 seconds.**

## 💡 What It Generates

| Output | Technologies |
|--------|-------------|
| 🐳 **Dockerfile** | Multi-stage builds, optimized for detected language |
| 🐙 **docker-compose.yml** | App + PostgreSQL/MongoDB/Redis auto-detected |
| ☸️ **Kubernetes Manifests** | Deployment, Service, Ingress, ConfigMap, HPA, Secrets |
| ⚡ **CI/CD Pipeline** | GitHub Actions → ECR → EKS deploy |
| ☁️ **AWS Terraform** | VPC, ECR, EKS, S3, RDS/DocumentDB, Security Groups |
| 📊 **ELK + Monitoring** | Elasticsearch, Logstash, Kibana, Prometheus, Grafana |
| 🔐 **Environment Config** | .env template, Nginx reverse proxy, Airflow DAG |

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python + FastAPI |
| **Frontend** | Vanilla HTML/CSS/JS with glassmorphism design |
| **AI Engine** | IBM watsonx Granite (with smart rule-based fallback) |
| **API** | GitHub REST API (public repo analysis) |
| **Generates** | Docker, Kubernetes, Terraform, GitHub Actions, ELK, Nginx, Airflow |
| **Built With** | IBM Bob IDE |

## 🚀 Getting Started

```bash
git clone https://github.com/AbhishekKharat04/repo-sage.git
cd repo-sage
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

## 🤖 IBM watsonx (Optional)

Enter your IBM Cloud API Key and watsonx Project ID in the UI for AI-enhanced analysis. Without credentials, ShipSage uses smart rule-based generation that detects 20+ languages/frameworks.

## 📁 Project Structure

```
repo-sage/
├── main.py              # FastAPI server
├── analyzer.py          # GitHub repo analyzer + stack detection
├── generators.py        # DevOps config generators (Docker, K8s, AWS, etc.)
├── templates/
│   └── index.html       # Premium dark-themed UI
├── requirements.txt
├── bob_sessions/        # IBM Bob IDE session evidence
├── FEATURES.md
├── SETUP.md
└── README.md
```

## 🏆 Why ShipSage

- ✅ **Unique concept** — no other hackathon project generates full DevOps pipelines
- ✅ **Real IBM watsonx integration** — uses Granite-13b-instruct-v2
- ✅ **Massive B2B value** — saves 2-3 days of DevOps setup per project
- ✅ **7 production-ready outputs** — Docker, K8s, CI/CD, AWS, ELK, Nginx, Airflow
- ✅ **Works without API keys** — smart fallback ensures demo always works
- ✅ **Premium UI** — glassmorphism, gradient animations, responsive design

## 🤝 Team

Built by **Team ShipSage** — Abhishek Kharat & Pratham Panchmukh

---

*Built with 🚀 for IBM Bob Hackathon 2026 · Powered by IBM watsonx*
