#!/bin/bash
# Orca Core Azure Deployment Script
# This script deploys Orca Core to Azure Kubernetes Service

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
K8S_DIR="$PROJECT_ROOT/k8s"
ENV_FILE="$PROJECT_ROOT/.env.local"

# Default values
ENVIRONMENT="dev"
RESOURCE_GROUP_NAME="orcacore-rg"
AKS_NAME=""
NAMESPACE="orca-core"
IMAGE_TAG="latest"
ACR_NAME=""
DRY_RUN=false

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Azure CLI is installed
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI is not installed. Please install it first:"
        log_error "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check if kubectl is installed
    if ! command -v kubectl >/dev/null 2>&1; then
        log_error "kubectl is not installed. Please install it first:"
        log_error "  https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    # Check if Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed. Please install it first:"
        log_error "  https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check if user is logged in to Azure
    if ! az account show >/dev/null 2>&1; then
        log_error "You are not logged in to Azure. Please run: az login"
        exit 1
    fi

    log_success "Prerequisites check completed"
}

# Function to load environment variables
load_environment() {
    log_info "Loading environment variables..."

    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        log_error "Please run 'make configure-azure-openai' first to create the environment file"
        exit 1
    fi

    # Source the environment file
    set -a
    source "$ENV_FILE"
    set +a

    # Set variables from environment
    ENVIRONMENT="${ORCA_ENVIRONMENT:-dev}"
    RESOURCE_GROUP_NAME="$AZURE_RESOURCE_GROUP"
    AKS_NAME="orca-aks-$ENVIRONMENT"
    ACR_NAME="orcacoreacr$ENVIRONMENT"

    log_success "Environment variables loaded successfully"
}

# Function to validate Azure resources
validate_azure_resources() {
    log_info "Validating Azure resources..."

    # Check if resource group exists
    if ! az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        log_error "Resource group '$RESOURCE_GROUP_NAME' does not exist"
        log_error "Please run the bootstrap script first to create the infrastructure"
        exit 1
    fi

    # Check if AKS cluster exists
    if ! az aks show --resource-group "$RESOURCE_GROUP_NAME" --name "$AKS_NAME" >/dev/null 2>&1; then
        log_error "AKS cluster '$AKS_NAME' does not exist"
        log_error "Please run the bootstrap script first to create the infrastructure"
        exit 1
    fi

    # Check if ACR exists
    if ! az acr show --name "$ACR_NAME" >/dev/null 2>&1; then
        log_error "ACR '$ACR_NAME' does not exist"
        log_error "Please run the bootstrap script first to create the infrastructure"
        exit 1
    fi

    log_success "Azure resources validation completed"
}

# Function to get AKS credentials
get_aks_credentials() {
    log_info "Getting AKS credentials..."

    az aks get-credentials \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$AKS_NAME" \
        --overwrite-existing

    # Verify connection
    if kubectl cluster-info >/dev/null 2>&1; then
        log_success "AKS credentials configured successfully"
        log_info "Current context: $(kubectl config current-context)"
    else
        log_error "Failed to configure AKS credentials"
        exit 1
    fi
}

# Function to build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."

    # Login to ACR
    log_info "Logging in to ACR: $ACR_NAME"
    az acr login --name "$ACR_NAME"

    # Build and push Orca Core API image
    local api_image="$ACR_NAME.azurecr.io/orca-core-api:$IMAGE_TAG"
    log_info "Building API image: $api_image"

    docker build \
        -t "$api_image" \
        -f "$PROJECT_ROOT/Dockerfile" \
        "$PROJECT_ROOT"

    # Push image
    log_info "Pushing API image to ACR..."
    docker push "$api_image"

    log_success "Docker images built and pushed successfully"
}

# Function to create Kubernetes namespace
create_namespace() {
    log_info "Creating Kubernetes namespace: $NAMESPACE"

    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_warning "Namespace '$NAMESPACE' already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace created successfully"
    fi
}

# Function to create Kubernetes secrets
create_k8s_secrets() {
    log_info "Creating Kubernetes secrets..."

    # Get secrets from Key Vault
    local key_vault_name="orca-keyvault-$ENVIRONMENT"

    # Create secret for Azure OpenAI
    local openai_api_key=$(az keyvault secret show \
        --vault-name "$key_vault_name" \
        --name "azure-openai-api-key" \
        --query "value" \
        --output tsv)

    local openai_endpoint=$(az keyvault secret show \
        --vault-name "$key_vault_name" \
        --name "azure-openai-endpoint" \
        --query "value" \
        --output tsv)

    local openai_deployment=$(az keyvault secret show \
        --vault-name "$key_vault_name" \
        --name "azure-openai-deployment" \
        --query "value" \
        --output tsv)

    # Create Kubernetes secret
    kubectl create secret generic orca-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=AZURE_OPENAI_API_KEY="$openai_api_key" \
        --from-literal=AZURE_OPENAI_ENDPOINT="$openai_endpoint" \
        --from-literal=AZURE_OPENAI_DEPLOYMENT="$openai_deployment" \
        --from-literal=ORCA_DECISION_MODE="RULES_PLUS_AI" \
        --from-literal=ORCA_USE_XGB="true" \
        --from-literal=ORCA_EXPLAIN_ENABLED="true" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_success "Kubernetes secrets created successfully"
}

# Function to deploy Kubernetes manifests
deploy_k8s_manifests() {
    log_info "Deploying Kubernetes manifests..."

    # Check if k8s directory exists
    if [ ! -d "$K8S_DIR" ]; then
        log_warning "Kubernetes manifests directory not found: $K8S_DIR"
        log_info "Creating basic Kubernetes manifests..."
        create_basic_k8s_manifests
    fi

    # Apply manifests
    local manifests=(
        "namespace.yaml"
        "configmap.yaml"
        "secret.yaml"
        "deployment.yaml"
        "service.yaml"
        "ingress.yaml"
    )

    for manifest in "${manifests[@]}"; do
        local manifest_path="$K8S_DIR/$manifest"
        if [ -f "$manifest_path" ]; then
            log_info "Applying manifest: $manifest"
            if [ "$DRY_RUN" = true ]; then
                kubectl apply --dry-run=client -f "$manifest_path"
            else
                kubectl apply -f "$manifest_path"
            fi
        else
            log_warning "Manifest not found: $manifest"
        fi
    done

    log_success "Kubernetes manifests deployed successfully"
}

# Function to create basic Kubernetes manifests
create_basic_k8s_manifests() {
    log_info "Creating basic Kubernetes manifests..."

    mkdir -p "$K8S_DIR"

    # Create namespace manifest
    cat > "$K8S_DIR/namespace.yaml" << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    name: $NAMESPACE
    environment: $ENVIRONMENT
EOF

    # Create deployment manifest
    cat > "$K8S_DIR/deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orca-core-api
  namespace: $NAMESPACE
  labels:
    app: orca-core-api
    environment: $ENVIRONMENT
spec:
  replicas: 2
  selector:
    matchLabels:
      app: orca-core-api
  template:
    metadata:
      labels:
        app: orca-core-api
        environment: $ENVIRONMENT
    spec:
      containers:
      - name: orca-core-api
        image: $ACR_NAME.azurecr.io/orca-core-api:$IMAGE_TAG
        ports:
        - containerPort: 8000
        env:
        - name: ORCA_DECISION_MODE
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: ORCA_DECISION_MODE
        - name: ORCA_USE_XGB
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: ORCA_USE_XGB
        - name: ORCA_EXPLAIN_ENABLED
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: ORCA_EXPLAIN_ENABLED
        - name: AZURE_OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: AZURE_OPENAI_API_KEY
        - name: AZURE_OPENAI_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: AZURE_OPENAI_ENDPOINT
        - name: AZURE_OPENAI_DEPLOYMENT
          valueFrom:
            secretKeyRef:
              name: orca-secrets
              key: AZURE_OPENAI_DEPLOYMENT
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

    # Create service manifest
    cat > "$K8S_DIR/service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: orca-core-api-service
  namespace: $NAMESPACE
  labels:
    app: orca-core-api
    environment: $ENVIRONMENT
spec:
  selector:
    app: orca-core-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
EOF

    log_success "Basic Kubernetes manifests created"
}

# Function to wait for deployment
wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."

    kubectl wait --for=condition=available \
        --timeout=300s \
        deployment/orca-core-api \
        --namespace="$NAMESPACE"

    log_success "Deployment is ready"
}

# Function to display deployment status
display_status() {
    log_info "Deployment Status:"
    echo

    # Show pods
    log_info "Pods:"
    kubectl get pods --namespace="$NAMESPACE" -o wide

    echo
    # Show services
    log_info "Services:"
    kubectl get services --namespace="$NAMESPACE"

    echo
    # Show ingress
    log_info "Ingress:"
    kubectl get ingress --namespace="$NAMESPACE" 2>/dev/null || log_warning "No ingress found"

    echo
    # Show deployment status
    log_info "Deployment Status:"
    kubectl get deployment orca-core-api --namespace="$NAMESPACE" -o wide
}

# Function to show help
show_help() {
    cat << EOF
Orca Core Azure Deployment Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Environment name (dev, staging, prod) [default: dev]
  -t, --tag TAG           Docker image tag [default: latest]
  -n, --namespace NS      Kubernetes namespace [default: orca-core]
  --dry-run               Show what would be deployed without actually deploying
  --skip-build            Skip building and pushing Docker images
  --skip-secrets          Skip creating Kubernetes secrets
  -h, --help              Show this help message

Examples:
  $0                                    # Deploy with default settings
  $0 -e staging -t v1.0.0              # Deploy staging with specific tag
  $0 --dry-run                         # Show what would be deployed
  $0 --skip-build                      # Deploy without rebuilding images

Prerequisites:
  - Azure CLI installed and logged in
  - kubectl installed
  - Docker installed
  - Environment file (.env.local) configured
  - Azure infrastructure deployed (run bootstrap script first)

EOF
}

# Parse command line arguments
SKIP_BUILD=false
SKIP_SECRETS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Starting Orca Core Azure deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $IMAGE_TAG"
    log_info "Namespace: $NAMESPACE"
    log_info "Dry Run: $DRY_RUN"
    echo

    check_prerequisites
    load_environment
    validate_azure_resources
    get_aks_credentials

    if [ "$SKIP_BUILD" = false ]; then
        build_and_push_images
    else
        log_info "Skipping Docker image build and push"
    fi

    create_namespace

    if [ "$SKIP_SECRETS" = false ]; then
        create_k8s_secrets
    else
        log_info "Skipping Kubernetes secrets creation"
    fi

    deploy_k8s_manifests

    if [ "$DRY_RUN" = false ]; then
        wait_for_deployment
        display_status

        log_success "Orca Core deployed successfully to Azure!"
        echo
        log_info "Next Steps:"
        echo "  1. Check deployment status: kubectl get pods --namespace=$NAMESPACE"
        echo "  2. View logs: kubectl logs -f deployment/orca-core-api --namespace=$NAMESPACE"
        echo "  3. Test the API: kubectl port-forward service/orca-core-api-service 8000:80 --namespace=$NAMESPACE"
        echo "  4. Access the application: http://localhost:8000"
    else
        log_info "Dry run completed. No changes were made."
    fi
}

# Run main function
main "$@"
