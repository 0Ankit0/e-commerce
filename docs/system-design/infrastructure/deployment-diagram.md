# Deployment Diagram

## Overview
Deployment diagrams showing the mapping of software components to hardware/infrastructure.

---

## Production Deployment Architecture

```mermaid
graph TB
    subgraph "Internet"
        Users[Users/Clients]
    end
    
    subgraph "Edge Layer"
        DNS[Route 53 DNS]
        CloudFront[CloudFront CDN]
        WAF[AWS WAF]
    end
    
    subgraph "AWS Region - Primary"
        subgraph "VPC - Production"
            subgraph "Public Subnet AZ-A"
                ALB_A[Application Load Balancer]
                NAT_A[NAT Gateway]
            end
            
            subgraph "Public Subnet AZ-B"
                ALB_B[Application Load Balancer]
                NAT_B[NAT Gateway]
            end
            
            subgraph "Private Subnet AZ-A - Application"
                EKS_A[EKS Worker Nodes]
            end
            
            subgraph "Private Subnet AZ-B - Application"
                EKS_B[EKS Worker Nodes]
            end
            
            subgraph "Private Subnet AZ-A - Data"
                RDS_Primary[(RDS Primary)]
                ElastiCache_A[(ElastiCache)]
            end
            
            subgraph "Private Subnet AZ-B - Data"
                RDS_Standby[(RDS Standby)]
                ElastiCache_B[(ElastiCache)]
            end
        end
        
        EKS_Control[EKS Control Plane<br>AWS Managed]
        MSK[Amazon MSK<br>Kafka Cluster]
        OpenSearch[Amazon OpenSearch]
        S3[S3 Buckets]
    end
    
    Users --> DNS
    DNS --> CloudFront
    CloudFront --> WAF
    WAF --> ALB_A
    WAF --> ALB_B
    
    ALB_A --> EKS_A
    ALB_B --> EKS_B
    
    EKS_A --> RDS_Primary
    EKS_B --> RDS_Primary
    EKS_A --> ElastiCache_A
    EKS_B --> ElastiCache_B
    
    EKS_A --> MSK
    EKS_B --> MSK
    EKS_A --> OpenSearch
    EKS_B --> OpenSearch
    EKS_A --> S3
    EKS_B --> S3
    
    RDS_Primary -.-> RDS_Standby
    ElastiCache_A <-.-> ElastiCache_B
    
    EKS_Control --> EKS_A
    EKS_Control --> EKS_B
```

---

## Kubernetes Deployment

```mermaid
graph TB
    subgraph "EKS Cluster"
        subgraph "Ingress"
            Ingress[NGINX Ingress Controller]
        end
        
        subgraph "API Layer Namespace"
            Gateway[Kong API Gateway<br>3 replicas]
        end
        
        subgraph "Services Namespace"
            subgraph "User Domain"
                AuthSvc[Auth Service<br>3 replicas]
                UserSvc[User Service<br>3 replicas]
            end
            
            subgraph "Catalog Domain"
                ProductSvc[Product Service<br>5 replicas]
                InventorySvc[Inventory Service<br>3 replicas]
                SearchSvc[Search Service<br>3 replicas]
            end
            
            subgraph "Order Domain"
                CartSvc[Cart Service<br>3 replicas]
                OrderSvc[Order Service<br>5 replicas]
                CheckoutSvc[Checkout Service<br>3 replicas]
            end
            
            subgraph "Payment Domain"
                PaymentSvc[Payment Service<br>3 replicas]
                PayoutSvc[Payout Service<br>2 replicas]
            end
            
            subgraph "Logistics Domain"
                ShipmentSvc[Shipment Service<br>3 replicas]
                TrackingSvc[Tracking Service<br>3 replicas]
            end
            
            subgraph "Support Domain"
                NotifSvc[Notification Service<br>3 replicas]
                AnalyticsSvc[Analytics Service<br>2 replicas]
            end
        end
        
        subgraph "Workers Namespace"
            OrderWorker[Order Worker<br>2 replicas]
            NotifWorker[Notification Worker<br>3 replicas]
            AnalyticsWorker[Analytics Worker<br>2 replicas]
        end
        
        subgraph "Monitoring Namespace"
            Prometheus[Prometheus]
            Grafana[Grafana]
            Jaeger[Jaeger]
        end
    end
    
    Ingress --> Gateway
    Gateway --> AuthSvc
    Gateway --> UserSvc
    Gateway --> ProductSvc
    Gateway --> OrderSvc
    Gateway --> PaymentSvc
    Gateway --> ShipmentSvc
```

---

## Service Deployment Specifications

### Deployment YAML Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: services
spec:
  replicas: 5
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
      - name: order-service
        image: ecr.aws/ecommerce/order-service:v1.2.3
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: service-config
              key: redis-url
```

---

## Deployment Environment Matrix

| Service | Dev | Staging | Production |
|---------|-----|---------|------------|
| Auth Service | 1 replica | 2 replicas | 3 replicas |
| User Service | 1 replica | 2 replicas | 3 replicas |
| Product Service | 1 replica | 2 replicas | 5 replicas |
| Inventory Service | 1 replica | 2 replicas | 3 replicas |
| Cart Service | 1 replica | 2 replicas | 3 replicas |
| Order Service | 1 replica | 2 replicas | 5 replicas |
| Payment Service | 1 replica | 2 replicas | 3 replicas |
| Shipment Service | 1 replica | 2 replicas | 3 replicas |
| Notification Service | 1 replica | 2 replicas | 3 replicas |

---

## Database Deployment

```mermaid
graph TB
    subgraph "RDS Deployment"
        subgraph "Primary Region"
            RDS_Primary[(Primary<br>db.r6g.2xlarge<br>Multi-AZ)]
            ReadReplica1[(Read Replica 1<br>db.r6g.xlarge)]
            ReadReplica2[(Read Replica 2<br>db.r6g.xlarge)]
        end
        
        subgraph "DR Region"
            RDS_DR[(DR Replica<br>db.r6g.2xlarge)]
        end
    end
    
    RDS_Primary -->|Sync Replication| ReadReplica1
    RDS_Primary -->|Sync Replication| ReadReplica2
    RDS_Primary -.->|Async Replication| RDS_DR
    
    subgraph "Application"
        WriteOps[Write Operations]
        ReadOps[Read Operations]
    end
    
    WriteOps --> RDS_Primary
    ReadOps --> ReadReplica1
    ReadOps --> ReadReplica2
```

---

## Redis Cluster Deployment

```mermaid
graph TB
    subgraph "ElastiCache Redis Cluster"
        subgraph "Shard 1"
            Primary1[(Primary)]
            Replica1A[(Replica)]
            Replica1B[(Replica)]
        end
        
        subgraph "Shard 2"
            Primary2[(Primary)]
            Replica2A[(Replica)]
            Replica2B[(Replica)]
        end
        
        subgraph "Shard 3"
            Primary3[(Primary)]
            Replica3A[(Replica)]
            Replica3B[(Replica)]
        end
    end
    
    Primary1 --> Replica1A
    Primary1 --> Replica1B
    Primary2 --> Replica2A
    Primary2 --> Replica2B
    Primary3 --> Replica3A
    Primary3 --> Replica3B
```

---

## Container Registry & CI/CD

```mermaid
graph LR
    subgraph "Development"
        Dev[Developer]
        Git[GitHub Repository]
    end
    
    subgraph "CI/CD Pipeline"
        Actions[GitHub Actions]
        Build[Build & Test]
        Scan[Security Scan]
        Push[Push to ECR]
    end
    
    subgraph "Container Registry"
        ECR[Amazon ECR]
    end
    
    subgraph "Deployment"
        ArgoCD[ArgoCD]
        DevCluster[Dev Cluster]
        StagingCluster[Staging Cluster]
        ProdCluster[Production Cluster]
    end
    
    Dev --> Git
    Git --> Actions
    Actions --> Build
    Build --> Scan
    Scan --> Push
    Push --> ECR
    ECR --> ArgoCD
    ArgoCD --> DevCluster
    ArgoCD --> StagingCluster
    ArgoCD --> ProdCluster
```

---

## Resource Allocation

| Component | Instance Type | vCPU | Memory | Storage |
|-----------|---------------|------|--------|---------|
| EKS Worker (App) | m6i.xlarge | 4 | 16 GB | 100 GB |
| EKS Worker (Workers) | m6i.large | 2 | 8 GB | 50 GB |
| RDS Primary | db.r6g.2xlarge | 8 | 64 GB | 1 TB |
| RDS Replica | db.r6g.xlarge | 4 | 32 GB | 1 TB |
| ElastiCache | cache.r6g.xlarge | 4 | 26 GB | - |
| OpenSearch | r6g.xlarge.search | 4 | 32 GB | 500 GB |
| MSK Broker | kafka.m5.xlarge | 4 | 16 GB | 1 TB |
