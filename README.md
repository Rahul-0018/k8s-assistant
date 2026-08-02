## 🤖 AI Chatbot Platform on Kubernetes

> **Cloud-native AI chatbot built with FastAPI, Groq LLM, Terraform, K3s, GitHub Actions, and Oracle Cloud Infrastructure (OCI).**

[![CI/CD Pipeline](https://github.com/Rahul-0018/k8s-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Rahul-0018/k8s-assistant/actions/workflows/ci.yml)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s-326CE5?logo=kubernetes&logoColor=white)](https://k3s.io/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)](https://terraform.io/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Oracle Cloud](https://img.shields.io/badge/Cloud-Oracle%20Cloud-F80000?logo=oracle&logoColor=white)](https://www.oracle.com/cloud/)

A cloud-native AI chatbot built with **FastAPI** and the **Groq LLM API**. The platform is deployed on **Oracle Cloud Infrastructure (OCI)** using **Terraform** for infrastructure provisioning, **K3s** for container orchestration, **GitHub Actions** for CI/CD, and includes security scanning and monitoring for a production-ready deployment.

---

## 🌐 Live Demo

- **Application:** [http://140.245.239.92:8000](http://140.245.239.92:8000)
- **Health Check:** [http://140.245.239.92:8000/docs](http://140.245.239.92:8000)

> **Note:** The live demo is hosted on Oracle Cloud Infrastructure (OCI) using Kubernetes (K3s). & The demo uses the Groq API. Response speed depends on API availability.

---

## 📖 System Architecture

```text
                             [ Developer ]
                                   │
                             git push main
                                   │
                                   ▼
                         [ GitHub Repository ]
                                   │
                                   ▼
                    [ GitHub Actions CI/CD Pipeline ]
 ┌──────────────────────────────────────────────────────────────────┐
 │ 1. Black & Flake8 Formatting    3. Build Multi-Arch Docker Image │
 │ 2. Trivy Vulnerability Scan     4. Push to Docker Hub / GHCR     │
 └──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                  [ Terraform-Provisioned OCI VCN ]
 ┌──────────────────────────────────────────────────────────────────┐
 │ Internet Gateway ─► Public Subnet ─► Security Lists              │
 │                                             │                    │
 │                                     Ubuntu Compute VM            │
 └─────────────────────────────────────────────┼────────────────────┘
                                               │
                                               ▼
                                   [ K3s Kubernetes Cluster ]
                                   ┌────────────────────────┐
                                   │        Pods            │
                                   └──────────┬─────────────┘
                                              │
                                              ▼
                                         [ Groq LLM API ]
                                              │
                                              ▼
                                            End Users
```

---

## ✨ Features

- 🤖 AI Chatbot with Groq LLM streaming responses
- ☸️ Kubernetes deployment using K3s
- 🚀 Infrastructure provisioning with Terraform
- 🔄 GitHub Actions CI/CD pipeline
- 🌿 GitOps deployment using Argo CD
- 📊 Monitoring with Prometheus & Grafana
- 🔒 Security using Trivy, TruffleHog, NetworkPolicy & Kubernetes Secrets

---

## 📦 Prerequisites

## Required Accounts

| Service | Sign Up |
|---------|---------|
| **Groq API** | https://console.groq.com |
| **GitHub** | https://github.com |
| **Oracle Cloud (OCI)** | https://cloud.oracle.com |

## Local Tools

```bash
sudo apt update
sudo apt install -y docker.io kubectl
```

Install Kind

https://kind.sigs.k8s.io/docs/user/quick-start/

Install Terraform

https://developer.hashicorp.com/terraform/install

---

## 🚀 Quick Start

## 1. Get a Groq API Key

- Create an account at https://console.groq.com/keys
- Copy your API key

```bash
export GROQ_API_KEY="gsk_your_key_here"
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/Rahul-0018/k8s-assistant.git

cd k8s-assistant
```

---

## 3. Run Locally

### Using Docker Compose

```bash
docker compose up --build
```

### Using Python

```bash
pip install -r requirements.txt

export GROQ_API_KEY="gsk_your_key"

uvicorn app:app --reload
```

Open

```
http://localhost:8000
```

---

## 4. Deploy to Local Kubernetes

Create Kind cluster

```bash
kind create cluster --name chatbotai
```

Deploy

```bash
./deploy.sh
```

Access

```bash
kubectl port-forward svc/chatbotai-service 8080:80 -n chatbotai
```

Open

```
http://localhost:8080
```

---

## 5. Deploy to Oracle Cloud (OCI)

```bash
cd terraform

cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`

```bash
terraform init

terraform plan

terraform apply
```

SSH into the VM

```bash
ssh -i ~/.ssh/id_rsa opc@$(terraform output -raw public_ip)
```

Clone the repository and deploy the Kubernetes manifests.

---

# ☸️ Kubernetes Deployment

## Directory Structure

```text
k8s/
├── namespace.yaml
├── configmap.yaml
├── deployment.yaml
├── service.yaml
├── ingress.yaml
├── networkpolicy.yaml
├── pdb.yaml
└── servicemonitor.yaml
```

## Deployment Order

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/servicemonitor.yaml
```

---

# 🔄 CI/CD Pipeline

The GitHub Actions workflow performs:

- ✅ Black & Flake8 formatting
- 🔒 Trivy vulnerability scanning
- 🔑 TruffleHog secret scanning
- 📦 Multi-architecture Docker image build
- 🚀 Push image to Docker Hub / GHCR
- 🧪 Automated testing
- 🌿 GitOps deployment

---

# 🌿 GitOps with Argo CD

Install Argo CD

```bash
kubectl create namespace argocd

kubectl apply -n argocd \
-f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Port-forward

```bash
kubectl port-forward svc/argocd-server -n argocd 8081:443
```

Login

```bash
argocd login localhost:8081 --insecure
```

Register the repository

```bash
argocd repo add https://github.com/YOUR_USERNAME/k8s-assistant

kubectl apply -f argocd-app.yaml
```

Every new Git push will automatically sync through Argo CD.

---

# 📊 Monitoring

Access Grafana

```bash
kubectl port-forward svc/monitoring-grafana -n monitoring 8082:80
```

Open

```
http://localhost:8082
```

Default Login

```
Username: admin
```

---

## 🔒 Security Features

| Layer | Implementation |
|--------|----------------|
| Container | Non-root user, read-only filesystem |
| Image | Trivy vulnerability scanning |
| Secrets | Kubernetes Secrets |
| Secret Detection | TruffleHog |
| Network | Kubernetes NetworkPolicy |
| Ingress | TLS & Rate Limiting |
| API | Environment variable injection |

---

## 📁 Repository Structure

```text
k8s-assistant/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── security-gate.sh
├── argocd-app.yaml
├── grafana-dashboard.json
├── .github/
│   └── workflows/
│       └── ci.yml
├── k8s/
├── terraform/
└── README.md
```

---

## 🙏 Credits

- Groq
- Oracle Cloud Infrastructure
- Kubernetes
- Terraform
- FastAPI
- GitHub Actions
- Prometheus
- Grafana
- Argo CD

---

## 🎉 Next Steps

- ⭐ Star the repository
- 🔑 Get a Groq API key
- 🚀 Deploy on Oracle Cloud
- 📊 Monitor with Grafana
- 🌿 Enable GitOps with Argo CD

Happy Chatting! 🤖
