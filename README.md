# 🚀 Groq AI Chatbot - Kubernetes Deployment

A production-ready AI chatbot powered by the **Groq API**, deployed on **Kubernetes** with full **CI/CD**, **GitOps**, **monitoring**, and **security scanning**.

## 📋 Table of Contents
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Groq API Free Tier](#groq-api-free-tier)
- [Local Development](#local-development)
- [Kubernetes Deployment](#kubernetes-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [GitOps with Argo CD](#gitops-with-argo-cd)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Browser  │────▶│  NGINX Ingress   │────▶│  K8s Service    │
└─────────────────┘     │  (TLS/Rate Limit)│     │  (Load Balance) │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┼───────────┐
                              │                           │           │
                        ┌─────▼─────┐              ┌──────▼────┐ ┌──▼────┐
                        │  Pod #1   │              │  Pod #2   │ │Pod #3 │
                        │(Chatbot)  │              │(Chatbot)  │ │(HPA)  │
                        └─────┬─────┘              └─────┬─────┘ └───────┘
                              │                          │
                              └──────────┬───────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │    Groq API (LPU)   │
                              │  https://api.groq.com│
                              └─────────────────────┘
```

---

## ✨ Features

- **🤖 AI Chatbot**: Streaming & non-streaming chat with multiple Groq models
- **☸️ Kubernetes**: Production-grade deployment with HPA, PDB, NetworkPolicy
- **🔄 CI/CD**: GitHub Actions with automated testing, security scanning, deployment
- **🌿 GitOps**: Argo CD for declarative continuous deployment
- **📊 Monitoring**: Prometheus + Grafana dashboards
- **🔒 Security**: Trivy scanning, non-root containers, NetworkPolicy, secret management
- **💰 100% Free Tier**: Oracle Cloud VMs + Groq free API + GitHub free tier

---

## 📦 Prerequisites

### Required Accounts (All Free)
| Service | Sign Up | Free Tier |
|---------|---------|-----------|
| **Groq API** | [console.groq.com](https://console.groq.com) | 30 RPM, 14,400 req/day (8B model) |
| **GitHub** | [github.com](https://github.com) | Unlimited public repos, 2,000 CI min/month |
| **Oracle Cloud** | [cloud.oracle.com](https://cloud.oracle.com) | 2x AMD VMs, 200GB storage, always free |

### Local Tools
```bash
# macOS
brew install docker kubectl kind terraform trivy

# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io kubectl
# Install kind: https://kind.sigs.k8s.io/docs/user/quick-start/
# Install terraform: https://developer.hashicorp.com/terraform/install
# Install trivy: https://aquasecurity.github.io/trivy/v0.18.3/installation/
```

---

## 🚀 Quick Start

### 1. Get Groq API Key
```bash
# Sign up at https://console.groq.com/keys (no credit card required)
# Copy your API key (starts with gsk_)
export GROQ_API_KEY="gsk_your_key_here"
```

### 2. Clone & Configure
```bash
git clone https://github.com/YOUR_USERNAME/groq-chatbot-k8s.git
cd groq-chatbot-k8s

# Update secret with your API key
sed -i "s/YOUR_GROQ_API_KEY_HERE/$GROQ_API_KEY/g" k8s/secret.yaml
```

### 3. Run Locally
```bash
# Docker Compose
docker-compose up --build

# Or Python directly
pip install -r requirements.txt
export GROQ_API_KEY="gsk_your_key"
uvicorn app:app --reload

# Open http://localhost:8000
```

### 4. Deploy to Kubernetes (Local)
```bash
# Create kind cluster
# kind create cluster --name chatbotai

# Deploy everything
./deploy.sh

# Port-forward to access
kubectl port-forward svc/chatbotai-service 8080:80 -n chatbotai
# Open http://localhost:8080
```

### 5. Deploy to Production (Oracle Cloud Free Tier)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Oracle Cloud credentials

terraform init
terraform plan
terraform apply

# SSH into the VM and deploy
ssh -i ~/.ssh/id_rsa opc@$(terraform output -raw public_ip)
# Inside VM, clone repo and run ./deploy.sh
```

---

## 🤖 Groq API Free Tier

Groq offers a **generous free tier** with no credit card required:

| Model | RPM | RPD | TPM | Speed |
|-------|-----|-----|-----|-------|
| `llama-3.1-8b-instant` | 30 | 14,400 | 6,000 | 560 TPS |
| `llama-3.3-70b-versatile` | 30 | 1,000 | 12,000 | 280 TPS |
| `meta-llama/llama-4-scout` | 30 | 1,000 | 30,000 | 594 TPS |
| `openai/gpt-oss-20b` | 30 | 1,000 | 8,000 | 1,000 TPS |
| `qwen/qwen3-32b` | 60 | 1,000 | 6,000 | 400 TPS |

**Key Points:**
- Rate limits are **per organization**, not per API key
- **Cached tokens don't count** toward rate limits
- Returns HTTP 429 with `retry-after` header when limits hit
- Sign up at [console.groq.com](https://console.groq.com)

---

## 💻 Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export GROQ_API_KEY="gsk_your_key"
export GROQ_MODEL="llama-3.1-8b-instant"

# 3. Run tests
pytest -v

# 4. Run app
uvicorn app:app --reload --port 8000

# 5. Test API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what is DevOps?"}'
```

---

## ☸️ Kubernetes Deployment

### Directory Structure
```
k8s/
├── namespace.yaml          # groq-chatbot namespace
├── configmap.yaml          # App configuration (non-sensitive)
├── secret.yaml             # Groq API key (NEVER commit real values)
├── deployment.yaml         # App deployment + HPA
├── service.yaml            # ClusterIP service
├── ingress.yaml            # NGINX Ingress with TLS
├── networkpolicy.yaml      # Firewall rules
├── pdb.yaml                # Pod disruption budget
└── servicemonitor.yaml     # Prometheus scraping
```

### Deployment Order
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml        # Edit first!
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml       # Requires domain + cert-manager
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/servicemonitor.yaml
```

### Or use the deploy script:
```bash
./deploy.sh
```

---

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs:

1. **🧪 Test**: Run pytest, check formatting with Black
2. **🔒 Security Scan**: Trivy vulnerability scan, TruffleHog secret detection
3. **📦 Build & Push**: Multi-arch Docker image to GHCR with layer caching
4. **🚀 Deploy Staging**: Auto-deploy to staging environment
5. **🏭 Deploy Production**: Manual approval → deploy to production with smoke tests

### Required GitHub Secrets
| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | Your Groq API key |
| `KUBECONFIG_STAGING` | Base64-encoded kubeconfig for staging |
| `KUBECONFIG_PROD` | Base64-encoded kubeconfig for production |

---

## 🌿 GitOps with Argo CD

```bash
# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Port-forward UI
kubectl port-forward svc/argocd-server -n argocd 8081:443

# Login (default: admin / initial password from argocd admin initial-password)
argocd login localhost:8081 --insecure

# Register repo and create app
argocd repo add https://github.com/YOUR_USERNAME/groq-chatbot-k8s
kubectl apply -f argocd-app.yaml

# Now any git push automatically deploys! 🎉
```

---

## 📊 Monitoring

### Access Grafana
```bash
# Port-forward Grafana
kubectl port-forward svc/monitoring-grafana -n monitoring 8082:80

# Login: admin / prom-operator
# Open http://localhost:8082
# Import dashboard from grafana-dashboard.json
```

### Key Metrics
- **Request Rate**: RPM to Groq API (stay under 30!)
- **Error Rate**: 5xx responses
- **Latency**: p95 response time
- **Pod CPU/Memory**: HPA scaling triggers
- **HPA Replicas**: Auto-scaling behavior

---

## 🔒 Security Features

| Layer | Implementation |
|-------|---------------|
| **Container** | Non-root user (UID 1000), read-only root fs, distroless base |
| **Image Scan** | Trivy blocks HIGH/CRITICAL CVEs in CI |
| **Secrets** | Kubernetes Secrets, never in code, TruffleHog detection |
| **Network** | NetworkPolicy blocks all except required ports |
| **Ingress** | Rate limiting (10 RPS), TLS via cert-manager |
| **API** | No API key in image, injected via env var |

### Run Security Gate Locally
```bash
./security-gate.sh
```

---

## 🐛 Troubleshooting

### Pod stuck in Pending
```bash
kubectl describe pod -n groq-chatbot
# Check: Insufficient resources? Image pull error?
```

### Groq API 429 (Rate Limit)
```bash
# Check current usage
curl -H "Authorization: Bearer $GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models

# Switch to a model with higher limits (llama-3.1-8b-instant: 14,400/day)
```

### Image pull error
```bash
# Verify GHCR access
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_USERNAME \
  --docker-password=$GITHUB_TOKEN \
  -n groq-chatbot

# Add to deployment spec:
# imagePullSecrets:
# - name: ghcr-secret
```

### HPA not scaling
```bash
# Check metrics-server
kubectl get pods -n kube-system | grep metrics-server

# Check current metrics
kubectl top pods -n groq-chatbot
```

---

## 📁 Repository Structure

```
groq-chatbot-k8s/
├── app.py                      # FastAPI application
├── requirements.txt            # Python dependencies
├── test_app.py                 # Pytest tests
├── Dockerfile                  # Multi-stage build
├── docker-compose.yml          # Local development
├── deploy.sh                   # K8s deployment script
├── security-gate.sh            # Security checks
├── argocd-app.yaml             # GitOps application
├── grafana-dashboard.json      # Monitoring dashboard
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # GitHub Actions pipeline
├── k8s/                        # Kubernetes manifests
├── terraform/                  # Oracle Cloud infrastructure
└── README.md                   # This file
```

---

## 📝 License

MIT License - Free for personal and commercial use.

## 🙏 Credits

- **Groq** for the blazing-fast LPU inference API
- **Oracle Cloud** for the generous always-free tier
- **Kubernetes** community for the orchestration platform

---

## 🎉 Next Steps

1. ⭐ Star this repo
2. 🔑 Get your free Groq API key
3. 🚀 Deploy to Kubernetes
4. 📊 Monitor in Grafana
5. 🌿 Set up GitOps with Argo CD

**Happy chatting!** 🤖💬
