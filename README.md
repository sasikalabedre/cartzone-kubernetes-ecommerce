# Cartzone — Kubernetes E-Commerce Application

A containerized e-commerce application deployed on a multi-node Kubernetes cluster using Minikube. This project demonstrates application deployment, database persistence, networking, autoscaling, availability, and automated database backups.

## Architecture

```text
                    User / Browser
                          |
                          v
                 cartzone.local
                          |
                          v
                  Kubernetes Ingress
                          |
                          v
                    Web Service
                          |
                          v
                  Nginx Web Pods (2)
                          |
                    /api requests
                          |
                          v
                    API Service
                          |
                          v
                  Flask API Pods (2+)
                          |
                          v
                 PostgreSQL Service
                          |
                          v
                  PostgreSQL Pod
                          |
                          v
                 Persistent Volume
```

### Backup Architecture

```text
              Kubernetes CronJob
               (Every 5 Minutes)
                       |
                       v
                PostgreSQL pg_dump
                       |
                       v
                 SQL Backup File
                       |
                       v
                Backup Persistent
                     Volume
```

## Technology Stack

- **Kubernetes:** Application orchestration
- **Minikube:** Local multi-node Kubernetes cluster
- **Docker:** Container images
- **Python and Flask:** REST API
- **PostgreSQL 16:** Relational database
- **Nginx:** Static frontend and API reverse proxy
- **Kubernetes Ingress:** HTTP routing
- **ConfigMaps and Secrets:** Application configuration
- **PersistentVolumeClaims:** Database and backup storage
- **Horizontal Pod Autoscaler (HPA):** API autoscaling
- **PodDisruptionBudget (PDB):** Availability during voluntary disruptions
- **NetworkPolicy:** Restricts database access
- **CronJob:** Scheduled database backups

## Project Structure

```text
cartzone/
├── namespace/
├── config/
│   ├── configmap.yaml
│   └── secret.yaml
├── database/
│   ├── postgres-service.yaml
│   ├── postgres-pvc.yaml
│   └── postgres-statefulset.yaml
├── api/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── api-deployment.yaml
│   └── api-service.yaml
├── web/
│   ├── index.html
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── web-deployment.yaml
│   └── web-service.yaml
├── ingress/
│   └── ingress.yaml
├── health/
├── scaling/
│   └── api-hpa.yaml
├── security/
│   ├── api-pdb.yaml
│   └── postgres-network-policy.yaml
├── backup/
│   ├── backup-pvc.yaml
│   └── postgres-backup-cronjob.yaml
├── .gitignore
└── README.md
```

## Prerequisites

Install or configure the following:

- Docker
- Minikube
- kubectl
- Git
- A GitHub account

Verify the tools:

```bash
docker --version
minikube version
kubectl version --client
git --version
```

## 1. Start the Kubernetes Cluster

Start Minikube:

```bash
minikube start --nodes 3
kubectl get nodes
```

If your existing three-node cluster is already running, you do not need to recreate it.

Create the application namespace if it does not already exist:

```bash
kubectl create namespace work
```

## 2. Configure the Application

Apply the ConfigMap and Secret:

```bash
kubectl apply -f config/configmap.yaml
kubectl apply -f config/secret.yaml
```

The ConfigMap contains non-sensitive configuration. The Secret provides the database password to the PostgreSQL and API containers.

**Security:** Never commit real passwords or credentials to GitHub. Use a secure secret-management solution for production.

## 3. Deploy PostgreSQL

Create the database storage, service, and StatefulSet:

```bash
kubectl apply -f database/postgres-pvc.yaml
kubectl apply -f database/postgres-service.yaml
kubectl apply -f database/postgres-statefulset.yaml
```

Verify:

```bash
kubectl get pvc -n work
kubectl get statefulset -n work
kubectl get pods -n work
```

The database uses persistent storage so its data can survive PostgreSQL Pod replacement.

## 4. Build the Application Images

Build the API image:

```bash
cd ~/cartzone/api
minikube image build --all -t cartzone-api:v1 .
```

Build the frontend image:

```bash
cd ~/cartzone/web
minikube image build --all -t cartzone-web:v1 .
```

Return to the project directory:

```bash
cd ~/cartzone
```

## 5. Deploy the API and Frontend

Apply the API Deployment and Service:

```bash
kubectl apply -f api/api-deployment.yaml
kubectl apply -f api/api-service.yaml
```

Apply the frontend Deployment and Service:

```bash
kubectl apply -f web/web-deployment.yaml
kubectl apply -f web/web-service.yaml
```

Verify the application Pods and Services:

```bash
kubectl get pods -n work
kubectl get deployments -n work
kubectl get services -n work
```

Wait for the API and frontend Pods to become Ready.

## 6. Configure Ingress

Enable the Minikube Ingress addon:

```bash
minikube addons enable ingress
```

Apply the Ingress:

```bash
kubectl apply -f ingress/ingress.yaml
kubectl get ingress -n work
```

Get the Minikube IP:

```bash
minikube ip
```

Add the IP and hostname to `/etc/hosts` on your local machine, replacing the IP if necessary:

```text
192.168.49.2 cartzone.local
```

Edit the file using:

```bash
sudo nano /etc/hosts
```

Open the application in your browser:

http://cartzone.local

The frontend displays products and allows users to place orders through the API.

## 7. Verify Application Health

Check the API endpoint from inside the cluster:

```bash
kubectl run api-test \
  --image=curlimages/curl:latest \
  --restart=Never \
  --namespace=work \
  --rm -it \
  -- curl -s http://cartzone-api:5000/health
```

Check product records:

```bash
kubectl run api-test \
  --image=curlimages/curl:latest \
  --restart=Never \
  --namespace=work \
  --rm -it \
  -- curl -s http://cartzone-api:5000/products
```

## 8. Configure Autoscaling

Enable the Metrics Server addon:

```bash
minikube addons enable metrics-server
```

Apply the API Horizontal Pod Autoscaler:

```bash
kubectl apply -f scaling/api-hpa.yaml
```

Inspect the autoscaler:

```bash
kubectl get hpa -n work
kubectl describe hpa cartzone-api-hpa -n work
```

The HPA is configured with a minimum of two and a maximum of five API replicas, targeting average CPU utilization of 50%.

## 9. Configure Availability During Disruptions

Apply the API PodDisruptionBudget:

```bash
kubectl apply -f security/api-pdb.yaml
kubectl get pdb -n work
```

The PDB requires at least one API Pod to remain available during supported voluntary disruptions.

To practice draining a node:

```bash
kubectl drain minikube-m03 --ignore-daemonsets --delete-emptydir-data
```

After the exercise, restore scheduling on the node:

```bash
kubectl uncordon minikube-m03
kubectl get nodes
kubectl get pods -n work
```

Only drain a node when you understand the impact on other workloads running in the cluster.

## 10. Restrict Database Access

Apply the PostgreSQL NetworkPolicy:

```bash
kubectl apply -f security/postgres-network-policy.yaml
kubectl get networkpolicy -n work
```

The policy permits PostgreSQL traffic on TCP port 5432 from the Cartzone API and backup Pods. Other Pods in the namespace are not permitted by this ingress policy.

NetworkPolicy enforcement depends on support from the cluster's network plugin.

## 11. Configure Automated Database Backups

Apply the backup storage:

```bash
kubectl apply -f backup/backup-pvc.yaml
```

Apply the scheduled backup CronJob:

```bash
kubectl apply -f backup/postgres-backup-cronjob.yaml
```

Inspect the CronJob and Jobs:

```bash
kubectl get cronjob -n work
kubectl get jobs -n work
```

View the backup Job logs:

```bash
kubectl logs job/cartzone-backup-manual -n work
```

The CronJob runs every five minutes and uses `pg_dump` to create SQL backups on a persistent volume. The manual Job name above is for the test Job created during this lab; use the actual Job name if it has been removed.

The backup PVC stores backup files independently of the PostgreSQL data PVC.

### Verify Backup Files

A temporary inspection Pod can mount the backup PVC to inspect the files:

```bash
kubectl exec -n work cartzone-backup-inspect -- ls -lh /backups
```

Check a backup's SQL structure:

```bash
kubectl exec -n work cartzone-backup-inspect -- sh -c \
'grep -E "CREATE TABLE|COPY .* FROM stdin|INSERT INTO" /backups/cartzone-20261027-122512.sql'
```

The tested backup contained the `orders`, `products`, and `persistence_test` table definitions and data-export sections.

The SQL backup was inspected, but a complete database restore test is still required to validate recoverability.

Delete the temporary inspection Pod when finished:

```bash
kubectl delete pod cartzone-backup-inspect -n work
```

## 12. Useful Troubleshooting Commands

Check all resources in the application namespace:

```bash
kubectl get all -n work
```

Check persistent storage:

```bash
kubectl get pvc -n work
kubectl get pv
```

Inspect application logs:

```bash
kubectl logs deployment/cartzone-api -n work
kubectl logs deployment/cartzone-web -n work
kubectl logs statefulset/cartzone-postgres -n work
```

Inspect a Pod:

```bash
kubectl describe pod <pod-name> -n work
```

Inspect rollout status:

```bash
kubectl rollout status deployment/cartzone-api -n work
kubectl rollout history deployment/cartzone-api -n work
```

## 13. GitHub

Initialize Git if needed:

```bash
git init
git branch -M main
git add .
git status
```

Review staged files to ensure that no credentials, Secret manifests, or SQL backups will be committed.

Commit and push:

```bash
git commit -m "Add Cartzone Kubernetes e-commerce project"
git remote add origin https://github.com/sasikalabedre/cartzone-kubernetes-ecommerce.git
git push -u origin main
```

If `origin` already exists, update it instead:

```bash
git remote set-url origin https://github.com/sasikalabedre/cartzone-kubernetes-ecommerce.git
git push -u origin main
```

Repository: https://github.com/sasikalabedre/cartzone-kubernetes-ecommerce

## Learning Outcomes

- Deploying multi-tier applications on Kubernetes
- Building and using local container images
- Running PostgreSQL with persistent storage
- Exposing services through Kubernetes Ingress
- Configuring application health probes and resource limits
- Scaling API replicas with HPA
- Maintaining availability with PodDisruptionBudget
- Restricting database access with NetworkPolicy
- Scheduling database backups using CronJob
- Inspecting and validating SQL backup files

## Future Improvements

- Test a complete database restore into a separate database.
- Use a secure secret-management solution.
- Store backups outside the cluster for disaster recovery.
- Add TLS for HTTPS.
- Introduce CI/CD for image builds and deployments.
- Add application monitoring and centralized logging.

---

**Project:** Cartzone Kubernetes E-Commerce Application  

