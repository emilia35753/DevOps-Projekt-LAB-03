# LAB-03 — Kalkulator: CI/CD z ręcznym deploymentem

Pipeline CI/CD dla LAB-03. Aplikacja kalkulatora (Python/Flask) jest automatycznie budowana, testowana i publikowana do Azure Container Registry przy każdym pushu na `main`. Deployment do Azure Kubernetes Service i aktualizacja obrazu w klastrze są ręczne.

```
GitHub Repo → (build + test, GitHub Actions) → ACR → (update ręczny) → AKS
```

## Aplikacja

Flask, endpointy: `GET /health` (healthcheck), `GET /add`, `GET /subtract`, `GET /multiply` (np. `/add?a=2&b=3`). Pokryta testami jednostkowymi (`test_app.py`, `pytest`).

## Struktura repozytorium

```
.
├── app.py / test_app.py / requirements.txt / Dockerfile
├── .github/workflows/ci.yml     # pipeline GitHub Actions
├── k8s/deployment.yaml          # manifest K8s (Deployment + Service)
└── README.md
```

## Infrastruktura Azure (utworzona ręcznie)

| Zasób | Nazwa | Uwagi |
|---|---|---|
| Resource Group | `rg-lab03` | region dozwolony przez politykę subskrypcji |
| Azure Container Registry | `<nazwa-acr>` | SKU: Basic |
| Azure Kubernetes Service | `aks-lab03` | 1 węzeł, podłączony do ACR (`--attach-acr`) |

```bash
az group create --name rg-lab03 --location <region>
az acr create --resource-group rg-lab03 --name <nazwa-acr> --sku Basic --location <region>
az aks create --resource-group rg-lab03 --name aks-lab03 --node-count 1 \
  --generate-ssh-keys --attach-acr <nazwa-acr>
az aks get-credentials --resource-group rg-lab03 --name aks-lab03
```

> Domyślny region (`westeurope`) był odrzucany przez politykę subskrypcji (`RequestDisallowedByAzure`) — finalny region (`polandcentral`) dobrano eksperymentalnie spośród dozwolonych.

## Uwierzytelnianie do ACR

Service principal (`az ad sp create-for-rbac`) nie zadziałał — konto nie miało uprawnień w Azure AD (`Insufficient privileges to complete the operation`). Zastosowano uproszczone podejście — **ACR admin user**:

```bash
az acr update --name <nazwa-acr> --admin-enabled true
az acr credential show --name <nazwa-acr>
```

## Sekrety repozytorium GitHub

| Nazwa sekretu | Wartość |
|---|---|
| `ACR_LOGIN_SERVER` | `<nazwa-acr>.azurecr.io` |
| `ACR_USERNAME` | username z `az acr credential show` |
| `ACR_PASSWORD` | password z `az acr credential show` |

## Pipeline CI (`.github/workflows/ci.yml`)

Przy każdym pushu na `main`: checkout → instalacja zależności + `pytest` → logowanie do ACR → build i push obrazu z tagiem `${{ github.sha }}` (zamiast `:latest`, żeby jednoznacznie powiązać obraz z commitem).

## Deployment do AKS (ręczny)

`k8s/deployment.yaml` definiuje `Deployment` (1 replika) i `Service` typu `LoadBalancer`.

```bash
kubectl apply -f k8s/deployment.yaml
kubectl get pods
kubectl get svc app-svc
```

Po przydzieleniu publicznego IP: `curl http://<EXTERNAL-IP>/health`

### Aktualizacja obrazu po nowym buildzie

Nowy obraz trafia do ACR automatycznie, ale klaster **nie aktualizuje się sam**:

```bash
kubectl set image deployment/app app=<nazwa-acr>.azurecr.io/app:<git-sha>
kubectl rollout status deployment/app
```

## Wniosek

Pipeline automatyzuje tylko build → test → push. Deployment do AKS pozostaje w pełni manualny — bez ręcznego `kubectl set image` klaster nadal serwuje starą wersję, mimo nowego obrazu w ACR.
