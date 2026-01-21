# Network / Infrastructure Diagram

## Overview
Network topology and infrastructure layout for the e-commerce platform.

---

## Network Architecture Overview

```mermaid
graph TB
    subgraph "Internet"
        Users[Users]
        Partners[Partner APIs]
    end
    
    subgraph "AWS Edge Services"
        Route53[Route 53<br>DNS]
        CloudFront[CloudFront<br>CDN]
        WAF[AWS WAF]
        Shield[AWS Shield<br>DDoS Protection]
    end
    
    subgraph "VPC - 10.0.0.0/16"
        subgraph "Public Subnets"
            subgraph "AZ-A 10.0.1.0/24"
                ALB_A[ALB Node]
                NAT_A[NAT Gateway]
                Bastion_A[Bastion Host]
            end
            
            subgraph "AZ-B 10.0.2.0/24"
                ALB_B[ALB Node]
                NAT_B[NAT Gateway]
            end
        end
        
        subgraph "Private App Subnets"
            subgraph "AZ-A 10.0.10.0/24"
                EKS_A[EKS Nodes]
            end
            
            subgraph "AZ-B 10.0.11.0/24"
                EKS_B[EKS Nodes]
            end
        end
        
        subgraph "Private Data Subnets"
            subgraph "AZ-A 10.0.20.0/24"
                RDS_A[(RDS Primary)]
                Redis_A[(ElastiCache)]
            end
            
            subgraph "AZ-B 10.0.21.0/24"
                RDS_B[(RDS Standby)]
                Redis_B[(ElastiCache)]
            end
        end
        
        IGW[Internet Gateway]
        
        subgraph "VPC Endpoints"
            S3_EP[S3 Endpoint]
            ECR_EP[ECR Endpoint]
            Secrets_EP[Secrets Manager Endpoint]
        end
    end
    
    Users --> Route53
    Route53 --> CloudFront
    CloudFront --> Shield
    Shield --> WAF
    WAF --> IGW
    IGW --> ALB_A
    IGW --> ALB_B
    
    ALB_A --> EKS_A
    ALB_B --> EKS_B
    
    EKS_A --> NAT_A
    EKS_B --> NAT_B
    NAT_A --> IGW
    NAT_B --> IGW
    
    EKS_A --> RDS_A
    EKS_B --> RDS_A
    EKS_A --> Redis_A
    EKS_B --> Redis_B
    
    EKS_A --> S3_EP
    EKS_B --> S3_EP
    EKS_A --> ECR_EP
    EKS_B --> ECR_EP
```

---

## Subnet Design

| Subnet | CIDR | Type | AZ | Purpose |
|--------|------|------|-----|---------|
| public-a | 10.0.1.0/24 | Public | AZ-A | ALB, NAT, Bastion |
| public-b | 10.0.2.0/24 | Public | AZ-B | ALB, NAT |
| private-app-a | 10.0.10.0/24 | Private | AZ-A | EKS Workers |
| private-app-b | 10.0.11.0/24 | Private | AZ-B | EKS Workers |
| private-data-a | 10.0.20.0/24 | Private | AZ-A | RDS, ElastiCache |
| private-data-b | 10.0.21.0/24 | Private | AZ-B | RDS, ElastiCache |

---

## Security Groups

```mermaid
graph LR
    subgraph "Security Group Configuration"
        subgraph "sg-alb"
            ALB[ALB Security Group]
        end
        
        subgraph "sg-eks"
            EKS[EKS Security Group]
        end
        
        subgraph "sg-rds"
            RDS[RDS Security Group]
        end
        
        subgraph "sg-redis"
            Redis[Redis Security Group]
        end
        
        subgraph "sg-bastion"
            Bastion[Bastion Security Group]
        end
    end
    
    Internet[Internet 0.0.0.0/0] -->|443, 80| ALB
    ALB -->|3000-3010| EKS
    EKS -->|5432| RDS
    EKS -->|6379| Redis
    Bastion -->|22| EKS
    VPN[VPN/Office IP] -->|22| Bastion
```

### Security Group Rules

| Security Group | Type | Port | Source | Description |
|----------------|------|------|--------|-------------|
| sg-alb | Inbound | 443 | 0.0.0.0/0 | HTTPS from internet |
| sg-alb | Inbound | 80 | 0.0.0.0/0 | HTTP redirect |
| sg-eks | Inbound | 3000-3010 | sg-alb | From ALB |
| sg-eks | Inbound | 443 | EKS Control Plane | Kubernetes API |
| sg-rds | Inbound | 5432 | sg-eks | PostgreSQL from app |
| sg-redis | Inbound | 6379 | sg-eks | Redis from app |
| sg-bastion | Inbound | 22 | Office IP | SSH access |

---

## Network ACLs

```mermaid
graph TB
    subgraph "NACL Configuration"
        subgraph "Public Subnet NACL"
            PubIn[Inbound Rules]
            PubOut[Outbound Rules]
        end
        
        subgraph "Private App Subnet NACL"
            PrivAppIn[Inbound Rules]
            PrivAppOut[Outbound Rules]
        end
        
        subgraph "Private Data Subnet NACL"
            PrivDataIn[Inbound Rules]
            PrivDataOut[Outbound Rules]
        end
    end
```

| NACL | Rule | Type | Port | Source/Dest | Action |
|------|------|------|------|-------------|--------|
| Public | 100 | Inbound | 443 | 0.0.0.0/0 | Allow |
| Public | 110 | Inbound | 80 | 0.0.0.0/0 | Allow |
| Public | 120 | Inbound | 1024-65535 | 0.0.0.0/0 | Allow |
| Private-App | 100 | Inbound | 3000-3010 | 10.0.0.0/16 | Allow |
| Private-Data | 100 | Inbound | 5432 | 10.0.10.0/23 | Allow |
| Private-Data | 110 | Inbound | 6379 | 10.0.10.0/23 | Allow |

---

## Load Balancer Configuration

```mermaid
graph TB
    subgraph "Application Load Balancer"
        Listener443[HTTPS Listener :443]
        Listener80[HTTP Listener :80]
        
        subgraph "Target Groups"
            TG_Gateway[Kong Gateway TG<br>Port 8000]
            TG_Web[Web App TG<br>Port 3000]
        end
        
        subgraph "Rules"
            R1["/api/* → Kong Gateway"]
            R2["/* → Web App"]
        end
    end
    
    Listener443 --> R1
    Listener443 --> R2
    Listener80 -->|Redirect| Listener443
    
    R1 --> TG_Gateway
    R2 --> TG_Web
```

---

## VPC Endpoints

| Endpoint | Type | Service | Purpose |
|----------|------|---------|---------|
| S3 Endpoint | Gateway | com.amazonaws.region.s3 | S3 access without NAT |
| ECR Endpoint | Interface | com.amazonaws.region.ecr.api | Docker image pull |
| ECR DKR | Interface | com.amazonaws.region.ecr.dkr | Docker pull |
| Secrets Manager | Interface | com.amazonaws.region.secretsmanager | Secrets access |
| CloudWatch | Interface | com.amazonaws.region.logs | Log shipping |
| STS | Interface | com.amazonaws.region.sts | IAM auth |

---

## DNS Configuration

```mermaid
graph TB
    subgraph "Route 53"
        HostedZone[Hosted Zone<br>ecommerce.com]
        
        subgraph "Records"
            A_Root[A Record<br>ecommerce.com]
            A_API[A Record<br>api.ecommerce.com]
            A_Vendor[A Record<br>vendor.ecommerce.com]
            A_Admin[A Record<br>admin.ecommerce.com]
            CNAME_CDN[CNAME<br>cdn.ecommerce.com]
        end
        
        subgraph "Health Checks"
            HC1[API Health Check]
            HC2[Web Health Check]
        end
    end
    
    subgraph "Targets"
        CloudFront_Dist[CloudFront Distribution]
        ALB[Application Load Balancer]
    end
    
    A_Root --> CloudFront_Dist
    A_API --> ALB
    A_Vendor --> ALB
    A_Admin --> ALB
    CNAME_CDN --> CloudFront_Dist
    
    HC1 --> ALB
    HC2 --> ALB
```

---

## Traffic Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant DNS as Route 53
    participant CDN as CloudFront
    participant WAF as AWS WAF
    participant ALB as Load Balancer
    participant Pod as K8s Pod
    participant DB as Database
    
    User->>DNS: Resolve api.ecommerce.com
    DNS-->>User: ALB IP Address
    
    User->>CDN: GET /static/image.jpg
    CDN-->>User: Cached Content (Cache Hit)
    
    User->>WAF: POST /api/orders
    WAF->>WAF: Check Rules
    WAF->>ALB: Forward Request
    ALB->>Pod: Route to Service
    Pod->>DB: Query Data
    DB-->>Pod: Response
    Pod-->>ALB: Response
    ALB-->>WAF: Response
    WAF-->>User: Response
```

---

## Cross-Region Network

```mermaid
graph TB
    subgraph "Region A - Primary (us-east-1)"
        VPC_A[VPC 10.0.0.0/16]
        ALB_A[ALB]
        RDS_A[(RDS Primary)]
    end
    
    subgraph "Region B - DR (us-west-2)"
        VPC_B[VPC 10.1.0.0/16]
        ALB_B[ALB]
        RDS_B[(RDS Replica)]
    end
    
    VPC_Peering[VPC Peering Connection]
    VPC_A <--> VPC_Peering
    VPC_Peering <--> VPC_B
    
    Route53[Route 53<br>Health-Based Routing]
    Route53 -->|Active| ALB_A
    Route53 -.->|Failover| ALB_B
    
    RDS_A -.->|Async Replication| RDS_B
```

---

## Bandwidth & Latency Requirements

| Connection | Bandwidth | Latency Target | SLA |
|------------|-----------|----------------|-----|
| User → CDN | Unlimited | < 50ms | 99.9% |
| CDN → ALB | 10 Gbps | < 10ms | 99.95% |
| ALB → EKS | 25 Gbps | < 5ms | 99.95% |
| EKS → RDS | 10 Gbps | < 2ms | 99.95% |
| EKS → Redis | 10 Gbps | < 1ms | 99.95% |
| Cross-Region | 1 Gbps | < 100ms | 99.9% |
