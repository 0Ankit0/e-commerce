# Cloud Architecture Diagram

## Overview
Cloud architecture design for the e-commerce platform on AWS.

---

## AWS Architecture Overview

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "Global Services"
            Route53[Route 53]
            CloudFront[CloudFront]
            WAF[AWS WAF]
            IAM[IAM]
        end
        
        subgraph "Primary Region (us-east-1)"
            subgraph "Compute"
                EKS[Amazon EKS]
                Lambda[AWS Lambda]
            end
            
            subgraph "Storage"
                S3[Amazon S3]
                EBS[Amazon EBS]
            end
            
            subgraph "Database"
                RDS[(Amazon RDS<br>PostgreSQL)]
                ElastiCache[(ElastiCache<br>Redis)]
                OpenSearch[(OpenSearch)]
            end
            
            subgraph "Messaging"
                MSK[Amazon MSK<br>Kafka]
                SQS[Amazon SQS]
                SNS[Amazon SNS]
            end
            
            subgraph "Security"
                SecretsManager[Secrets Manager]
                KMS[AWS KMS]
                ACM[ACM]
            end
            
            subgraph "Monitoring"
                CloudWatch[CloudWatch]
                XRay[X-Ray]
            end
            
            subgraph "Networking"
                VPC[VPC]
                ALB[ALB]
                PrivateLink[PrivateLink]
            end
        end
        
        subgraph "DR Region (us-west-2)"
            EKS_DR[EKS - Standby]
            RDS_DR[(RDS - Replica)]
            S3_DR[S3 - Replica]
        end
    end
    
    Route53 --> CloudFront
    CloudFront --> WAF
    WAF --> ALB
    ALB --> EKS
    
    EKS --> RDS
    EKS --> ElastiCache
    EKS --> OpenSearch
    EKS --> MSK
    EKS --> S3
    
    EKS --> SecretsManager
    SecretsManager --> KMS
    
    CloudWatch --> EKS
    XRay --> EKS
    
    RDS -.->|Replication| RDS_DR
    S3 -.->|Replication| S3_DR
```

---

## Detailed AWS Service Architecture

```mermaid
graph TB
    subgraph "User Traffic"
        Users[Users]
    end
    
    subgraph "Edge & CDN"
        R53[Route 53<br>DNS + Health Checks]
        CF[CloudFront<br>Global CDN]
        WAF[AWS WAF<br>Web Security]
        Shield[AWS Shield<br>DDoS Protection]
    end
    
    subgraph "Load Balancing"
        ALB[Application Load Balancer<br>Layer 7 Routing]
    end
    
    subgraph "Container Platform"
        EKS[Amazon EKS]
        
        subgraph "EKS Node Groups"
            NG_App[App Node Group<br>m6i.xlarge x 6]
            NG_Worker[Worker Node Group<br>m6i.large x 4]
        end
        
        ECR[Amazon ECR<br>Container Registry]
    end
    
    subgraph "Serverless"
        Lambda[AWS Lambda<br>Event Processing]
        StepFunctions[Step Functions<br>Workflows]
    end
    
    subgraph "Data Stores"
        RDS[(Amazon RDS<br>PostgreSQL<br>Multi-AZ)]
        EC[(ElastiCache<br>Redis Cluster<br>3 Shards)]
        OS[(OpenSearch<br>3 Data Nodes)]
        DDB[(DynamoDB<br>Session Store)]
    end
    
    subgraph "Object Storage"
        S3_Assets[S3 - Static Assets]
        S3_Media[S3 - Product Images]
        S3_Logs[S3 - Logs]
        S3_Backups[S3 - Backups]
    end
    
    subgraph "Messaging"
        MSK[Amazon MSK<br>Kafka 3 Brokers]
        SQS[Amazon SQS<br>Standard Queues]
        SNS[Amazon SNS<br>Push Notifications]
        EventBridge[EventBridge<br>Event Bus]
    end
    
    subgraph "Notifications"
        SES[Amazon SES<br>Email]
        Pinpoint[Amazon Pinpoint<br>SMS/Push]
    end
    
    Users --> R53
    R53 --> CF
    CF --> Shield
    Shield --> WAF
    WAF --> ALB
    
    ALB --> EKS
    ECR --> EKS
    
    EKS --> RDS
    EKS --> EC
    EKS --> OS
    EKS --> DDB
    
    EKS --> MSK
    MSK --> Lambda
    Lambda --> SQS
    SQS --> StepFunctions
    
    EKS --> S3_Media
    CF --> S3_Assets
    
    Lambda --> SES
    Lambda --> Pinpoint
    EventBridge --> SNS
```

---

## Multi-Region Architecture

```mermaid
graph TB
    subgraph "Global"
        R53[Route 53<br>Latency-Based Routing]
        GlobalAccelerator[Global Accelerator]
        CloudFront[CloudFront<br>Global Edge]
    end
    
    subgraph "Primary Region - US-EAST-1"
        subgraph "VPC Primary"
            ALB_P[ALB]
            EKS_P[EKS Cluster]
            RDS_P[(RDS Primary)]
            Redis_P[(ElastiCache)]
        end
        
        S3_P[S3 Primary]
        MSK_P[MSK Cluster]
    end
    
    subgraph "Secondary Region - US-WEST-2"
        subgraph "VPC Secondary"
            ALB_S[ALB]
            EKS_S[EKS Cluster<br>Standby]
            RDS_S[(RDS Read Replica)]
            Redis_S[(ElastiCache)]
        end
        
        S3_S[S3 Replica]
    end
    
    subgraph "Asia Region - AP-SOUTH-1"
        subgraph "VPC Asia"
            ALB_A[ALB]
            EKS_A[EKS Cluster]
            RDS_A[(RDS Read Replica)]
        end
    end
    
    R53 --> GlobalAccelerator
    GlobalAccelerator -->|Active| ALB_P
    GlobalAccelerator -->|Passive| ALB_S
    GlobalAccelerator -->|Active| ALB_A
    
    CloudFront --> S3_P
    CloudFront --> S3_S
    
    RDS_P -.->|Async Replication| RDS_S
    RDS_P -.->|Async Replication| RDS_A
    S3_P -.->|Cross-Region Replication| S3_S
```

---

## Security Architecture

```mermaid
graph TB
    subgraph "Perimeter Security"
        WAF[AWS WAF<br>OWASP Rules]
        Shield[Shield Advanced<br>DDoS]
        Firewall[Network Firewall]
    end
    
    subgraph "Identity & Access"
        Cognito[Cognito<br>User Auth]
        IAM[IAM Roles]
        STS[STS<br>Temporary Credentials]
    end
    
    subgraph "Data Protection"
        KMS[AWS KMS<br>Key Management]
        SecretsManager[Secrets Manager<br>Credentials]
        ACM[ACM<br>SSL Certificates]
    end
    
    subgraph "Detection & Response"
        GuardDuty[GuardDuty<br>Threat Detection]
        SecurityHub[Security Hub<br>Centralized View]
        CloudTrail[CloudTrail<br>API Audit]
        Config[AWS Config<br>Compliance]
    end
    
    subgraph "Network Security"
        VPC[VPC]
        SecurityGroups[Security Groups]
        NACLs[NACLs]
        PrivateLink[PrivateLink]
    end
    
    WAF --> ALB
    Cognito --> API
    IAM --> EKS
    KMS --> RDS
    KMS --> S3
    SecretsManager --> EKS
    
    GuardDuty --> SecurityHub
    CloudTrail --> SecurityHub
    Config --> SecurityHub
```

---

## Monitoring & Observability

```mermaid
graph TB
    subgraph "Data Sources"
        EKS[EKS Pods]
        Lambda[Lambda Functions]
        RDS[(RDS)]
        ALB[ALB]
    end
    
    subgraph "Collection"
        CWAgent[CloudWatch Agent]
        FluentBit[Fluent Bit]
        OTEL[OpenTelemetry]
    end
    
    subgraph "Monitoring Services"
        CloudWatch[CloudWatch<br>Metrics & Logs]
        XRay[X-Ray<br>Tracing]
        Prometheus[Prometheus<br>Metrics]
    end
    
    subgraph "Visualization"
        CWDashboard[CloudWatch Dashboards]
        Grafana[Grafana]
    end
    
    subgraph "Alerting"
        SNS[SNS]
        PagerDuty[PagerDuty]
        Slack[Slack]
    end
    
    EKS --> CWAgent
    EKS --> FluentBit
    EKS --> OTEL
    
    Lambda --> CloudWatch
    RDS --> CloudWatch
    ALB --> CloudWatch
    
    CWAgent --> CloudWatch
    FluentBit --> CloudWatch
    OTEL --> XRay
    
    CloudWatch --> CWDashboard
    Prometheus --> Grafana
    
    CloudWatch --> SNS
    SNS --> PagerDuty
    SNS --> Slack
```

---

## Cost Optimization Architecture

```mermaid
graph TB
    subgraph "Compute Optimization"
        Spot[Spot Instances<br>Worker Nodes]
        Savings[Savings Plans<br>1-3 Year]
        Graviton[Graviton Instances<br>ARM64]
        Fargate[Fargate<br>Burst Workloads]
    end
    
    subgraph "Storage Optimization"
        S3IA[S3 Infrequent Access<br>Old Logs]
        Glacier[S3 Glacier<br>Archives]
        GP3[GP3 EBS<br>Cost-Effective]
    end
    
    subgraph "Database Optimization"
        Reserved[Reserved Instances<br>RDS/ElastiCache]
        Aurora[Aurora Serverless<br>Dev/Test]
        ReadReplica[Read Replicas<br>Read Scaling]
    end
    
    subgraph "Network Optimization"
        VPCEndpoints[VPC Endpoints<br>Reduce NAT]
        CloudFront[CloudFront<br>Reduce Origin Load]
    end
```

---

## AWS Services Summary

| Category | Service | Purpose |
|----------|---------|---------|
| **Compute** | EKS | Container orchestration |
| | Lambda | Event-driven functions |
| | Fargate | Serverless containers |
| **Storage** | S3 | Object storage |
| | EBS | Block storage |
| **Database** | RDS PostgreSQL | Primary database |
| | ElastiCache Redis | Caching |
| | OpenSearch | Full-text search |
| | DynamoDB | Session store |
| **Messaging** | MSK (Kafka) | Event streaming |
| | SQS | Message queues |
| | SNS | Pub/sub notifications |
| **Networking** | VPC | Network isolation |
| | ALB | Load balancing |
| | CloudFront | CDN |
| | Route 53 | DNS |
| **Security** | WAF | Web firewall |
| | KMS | Encryption |
| | Secrets Manager | Credentials |
| | IAM | Access control |
| **Monitoring** | CloudWatch | Metrics & logs |
| | X-Ray | Distributed tracing |

---

## Estimated Monthly Costs

| Component | Specification | Est. Monthly Cost |
|-----------|---------------|-------------------|
| EKS Cluster | Control plane + nodes | $1,500 |
| EC2 Instances | 10 x m6i.xlarge | $3,500 |
| RDS PostgreSQL | db.r6g.2xlarge Multi-AZ | $2,000 |
| ElastiCache | 3-shard cluster | $1,200 |
| OpenSearch | 3-node cluster | $1,500 |
| MSK | 3-broker cluster | $1,800 |
| S3 | 5 TB storage | $115 |
| CloudFront | 10 TB transfer | $850 |
| Data Transfer | 50 TB | $4,500 |
| **Total** | | **~$17,000/month** |

> Note: Costs are estimates and will vary based on actual usage.
