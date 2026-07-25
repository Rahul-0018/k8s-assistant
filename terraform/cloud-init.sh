#!/bin/bash
set -e

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker opc

# Install kind (Kubernetes in Docker)
curl -Lo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64
chmod +x /usr/local/bin/kind

# Install kubectl
curl -LO "https://dl.k8s/release/$(curl -L -s https://dl.k8s/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
mv kubectl /usr/local/bin/

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create kind cluster config
cat > /home/opc/kind-config.yaml << 'KINDEOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 8000
    hostPort: 8000
    protocol: TCP
KINDEOF

# Create cluster as opc user
su - opc -c "kind create cluster --config /home/opc/kind-config.yaml --name groq-chatbot"

# Install NGINX Ingress Controller
su - opc -c "kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"

# Wait for ingress controller
sleep 30
su - opc -c "kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s"

# Install cert-manager for TLS
su - opc -c "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml"

# Install Prometheus + Grafana (kube-prometheus-stack)
su - opc -c "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts"
su - opc -c "helm repo update"
su - opc -c "helm install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --wait"

# Create namespace and secret for chatbot
su - opc -c "kubectl create namespace groq-chatbot"
su - opc -c "kubectl create secret generic groq-chatbot-secrets -n groq-chatbot --from-literal=GROQ_API_KEY='${groq_api_key}'"

# Install Argo CD for GitOps
su - opc -c "kubectl create namespace argocd"
su - opc -c "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"

# Install metrics-server for HPA
su - opc -c "kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"

# Port-forward scripts for easy access
cat > /home/opc/port-forward.sh << 'PFEOF'
#!/bin/bash
# Port forward for local access
kubectl port-forward svc/groq-chatbot-service 8000:80 -n groq-chatbot &
echo "Chatbot available at http://localhost:8000"
PFEOF
chmod +x /home/opc/port-forward.sh
chown opc:opc /home/opc/port-forward.sh

echo "=== Setup Complete ==="
echo "Cluster: kind-groq-chatbot"
echo "Run 'kubectl get nodes' to verify"
echo "Run '/home/opc/port-forward.sh' to access the app"
