# SIH26002 — Deployment Readiness & Production Roadmap

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Purpose:** Comprehensive gap analysis comparing current local evaluation architecture against Enterprise Production standards.  

---

## 1. Environment Comparison Matrix

| Architectural Dimension | Current Development / Evaluation (Local) | Staging Environment (Target) | Production Environment (Target) |
| :--- | :--- | :--- | :--- |
| **Hosting & Compute** | Local Windows 11 Host | Dedicated Cloud VM (e.g. Ubuntu 22.04 LTS on AWS/GCP/MeghRaj) | High-Availability Auto-Scaling Cluster behind Load Balancer |
| **Process Manager** | Direct PowerShell / Command Prompt | Systemd services for Django, Gunicorn, Next.js | Systemd / Kubernetes Pods with health/readiness probes |
| **Web Server / Gateway** | Django `runserver` & Next.js `npm run dev` | Nginx reverse proxy terminating HTTPS | Nginx / Cloudflare WAF + TLS 1.3 with DDoS mitigation |
| **Database** | Local PostgreSQL 16 + PostGIS 3.4 | Managed PostgreSQL with PostGIS (e.g. AWS RDS / Azure Postgres) | Multi-AZ Primary-Standby Replica with automated failover |
| **Spatial Engine** | Native PostGIS (Point/LineString) | PostGIS with read-replica for heavy GIS queries | PostGIS cluster with connection pooling (PgBouncer) |
| **Secrets Management** | `.env` / environment variable defaults | HashiCorp Vault or Cloud Secret Manager | Cloud KMS / HSM with automatic credential rotation |
| **Background Tasks** | Synchronous execution / mock queues | Redis 7 + Celery workers | Redis Cluster + Celery with dedicated high-priority queues |
| **Observability** | Console logs + `X-Correlation-ID` header | Prometheus + Grafana dashboard | Distributed OpenTelemetry + ELK / Datadog APM |
| **Data Backups** | Local manual SQL dumps | Nightly automated snapshots (7-day retention) | Continuous WAL archiving (Point-in-Time Recovery to 30 days) |
| **Mobile App (Flutter)** | Static codebase & local debug APK | Internal distribution (Firebase App Distribution) | Google Play Store + MDM for state logistics fleets |
| **External Integrations** | Configured domain telemetry fallbacks | Sandboxed government API endpoints (IMD/Bhuvan) | Live authenticated government API feeds with circuit breakers |
| **AI/ML Serving** | In-process Scikit-learn inference (`joblib`) | Dedicated MLflow model registry | Triton / TorchServe microservice with model drift monitoring |

---

## 2. Implemented vs Production Gap Analysis

### 2.1 What is Implemented Today
- Clean separation of presentation, business logic, analytics, and spatial persistence layers.
- Full DRF serialization and OpenAPI 3.0 schema generation (`drf-spectacular`).
- Role-Based Access Control (`ADMIN`, `DISPATCHER`, `DRIVER`, `SHIPPER`).
- Request correlation tracking with `X-Correlation-ID` injected into all mutating requests.
- Sub-100ms multi-modal Dijkstra routing with PostGIS LineString geometry synthesis.
- Cryptographic offline graph bundle generation with SHA-256 integrity verification.
- Safe demo reset mechanism preserving real database records while clearing simulation data.
- Live 15-subsystem health diagnostic probe (`GET /api/v1/demo/readiness/`).

### 2.2 Production Requirements for Nationwide Scale
1. **NIC / MeghRaj Cloud Deployment:** Migration to Government of India certified cloud infrastructure (MeghRaj / NIC Cloud) to comply with data sovereignty regulations.
2. **PgBouncer Connection Pooling:** Essential when 10,000+ drivers concurrently submit sync batches.
3. **Live Telecom Integration:** Replacing mock notification providers with active CDAC / NIC SMS Gateway and telecom USSD providers for non-smartphone drivers.
4. **Live Satellite Telemetry Ingestion:** Transitioning from domain-calibrated fallbacks to active API keys for ISRO Bhuvan CartoDEM and IMD AWS feeds.
5. **Hardware Security Modules (HSM):** Enterprise signing for driver manifests and freight bill-of-lading documents.

---

## 3. Production Rollback & Disaster Recovery Strategy

1. **Database Rollback:** Zero-downtime schema migrations using Django `RunPython` reverse functions; Point-in-Time Recovery (PITR) enabled via PostgreSQL Write-Ahead Logs.
2. **Application Rollback:** Blue/Green deployment strategy allowing instant rollback to previous stable release in $< 10\text{ seconds}$ if health checks fail.
3. **Offline Client Resilience:** If the central server experiences an outage, drivers continue navigating using cached local graph bundles; synchronization resumes automatically upon server restoration.
