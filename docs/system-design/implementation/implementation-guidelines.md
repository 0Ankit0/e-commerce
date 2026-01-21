# Implementation Guidelines

## Overview
This document provides implementation guidelines, coding standards, and best practices for developing the e-commerce platform.

---

## Technology Stack

### Backend Services

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | Latest |
| API Layer | REST | OpenAPI 3.0 |
| Database ORM | SQLAlchemy | 2.x |
| Validation | Pydantic | 2.x |
| Testing | pytest + httpx | Latest |
| Async | asyncio + uvicorn | Latest |

### Database

| Environment | Technology | Purpose |
|-------------|------------|----------|
| Production | PostgreSQL 15+ | Primary database |
| Testing | SQLite | Unit/integration tests |
| Caching | Redis | Sessions, hot data |

### Frontend Applications

| Application | Technology |
|-------------|------------|
| Customer Web | Next.js 14 |
| Vendor Portal | Next.js / React |
| Admin Dashboard | Next.js / React |
| Mobile Apps | Flutter |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Container | Docker |
| Orchestration | Kubernetes (EKS) |
| CI/CD | GitHub Actions |
| IaC | Terraform |

---

## Project Structure

```
/services
├── auth-service/
│   ├── app/
│   │   ├── api/           # Routers, endpoints
│   │   ├── core/          # Config, security, deps
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── repositories/  # Data access
│   │   └── utils/         # Helpers
│   ├── tests/
│   ├── alembic/           # Migrations
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── Pipfile
│
├── order-service/
├── product-service/
├── payment-service/
├── logistics-service/
└── notification-service/

/apps
├── customer-web/          # Next.js app
├── vendor-portal/         # Next.js / React app
├── admin-dashboard/       # Next.js / React app
└── mobile-app/            # Flutter app

/packages
├── shared-types/         # TypeScript types
├── ui-components/        # Shared UI library
└── utils/               # Common utilities

/infrastructure
├── terraform/           # IaC definitions
├── k8s/                # Kubernetes manifests
└── docker/             # Docker configs
```

---

## Coding Standards

### Python Configuration (pyproject.toml)

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Ruff Linter Configuration

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.ruff.per-file-ignores]
"tests/*" = ["S101"]
```

---

## API Implementation Pattern

### Router Layer (FastAPI)

```python
# app/api/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """Create a new order."""
    order_service = OrderService(db)
    order = await order_service.create_order(
        user_id=current_user.id,
        order_data=order_data
    )
    return order
```

### Service Layer

```python
# app/services/order_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.schemas.order import OrderCreate
from app.repositories.order_repository import OrderRepository
from app.core.events import EventPublisher


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.event_publisher = EventPublisher()

    async def create_order(
        self, user_id: UUID, order_data: OrderCreate
    ) -> Order:
        # Business logic
        order = Order(
            user_id=user_id,
            address_id=order_data.address_id,
            items=order_data.items,
        )

        # Persist
        saved_order = await self.order_repo.save(order)

        # Publish event
        await self.event_publisher.publish(
            "order.created",
            {"order_id": str(saved_order.id), "user_id": str(user_id)}
        )

        return saved_order
```

### Repository Pattern

```python
# app/repositories/order_repository.py
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, id: UUID) -> Optional[Order]:
        query = (
            select(Order)
            .where(Order.id == id)
            .options(selectinload(Order.items))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def save(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def find_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[Order]:
        query = (
            select(Order)
            .where(Order.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Order.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
```

---

## Error Handling

### Custom Exception Classes

```python
# app/core/exceptions.py
from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__("VALIDATION_ERROR", message, 400, details)


class NotFoundException(AppException):
    def __init__(self, resource: str):
        super().__init__("NOT_FOUND", f"{resource} not found", 404)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__("UNAUTHORIZED", message, 401)
```

### Exception Handler

```python
# app/core/exception_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(
    request: Request, exc: AppException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request.headers.get("x-request-id"),
        },
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
            "request_id": request.headers.get("x-request-id"),
        },
    )
```

---

## Database Models & Migrations

### SQLAlchemy Model Example

```python
# app/models/order.py
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List

from sqlalchemy import ForeignKey, String, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order")
    user: Mapped["User"] = relationship(back_populates="orders")
```

### Alembic Migration Commands

```bash
# Initialize alembic (first time only)
pipenv run alembic init alembic

# Create migration
pipenv run alembic revision --autogenerate -m "add_orders_table"

# Apply migrations (production)
pipenv run alembic upgrade head

# Rollback one migration
pipenv run alembic downgrade -1
```

### Database Configuration

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Use PostgreSQL in production, SQLite for testing
if settings.TESTING:
    SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
else:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=settings.DEBUG)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Testing Strategy

### Unit Tests (pytest)

```python
# tests/unit/services/test_order_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.order_service import OrderService
from app.schemas.order import OrderCreate


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def order_service(mock_db):
    service = OrderService(mock_db)
    service.order_repo = AsyncMock()
    service.event_publisher = AsyncMock()
    return service


class TestOrderService:
    @pytest.mark.asyncio
    async def test_create_order_success(self, order_service):
        # Arrange
        user_id = uuid4()
        order_data = OrderCreate(
            address_id=uuid4(),
            payment_method="card"
        )
        saved_order = MagicMock(id=uuid4())
        order_service.order_repo.save.return_value = saved_order

        # Act
        result = await order_service.create_order(user_id, order_data)

        # Assert
        assert result.id == saved_order.id
        order_service.event_publisher.publish.assert_called_once_with(
            "order.created",
            {"order_id": str(saved_order.id), "user_id": str(user_id)}
        )
```

### Integration Tests (httpx + pytest)

```python
# tests/integration/test_orders.py
import pytest
from httpx import AsyncClient

from app.main import app
from tests.utils import get_test_token, create_test_db


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers():
    token = await get_test_token()
    return {"Authorization": f"Bearer {token}"}


class TestOrdersAPI:
    @pytest.mark.asyncio
    async def test_create_order_success(self, client, auth_headers):
        response = await client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "address_id": "addr-uuid",
                "payment_method": "card"
            }
        )

        assert response.status_code == 201
        assert "order_number" in response.json()["data"]["order"]
```

### Test Configuration (conftest.py)

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_engine):
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()
```
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run linting
        run: npm run lint
      
      - name: Run tests
        run: npm test -- --coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t $ECR_REGISTRY/$SERVICE_NAME:$GITHUB_SHA .
      
      - name: Push to ECR
        run: docker push $ECR_REGISTRY/$SERVICE_NAME:$GITHUB_SHA

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to EKS
        run: |
          kubectl set image deployment/$SERVICE_NAME \
            $SERVICE_NAME=$ECR_REGISTRY/$SERVICE_NAME:$GITHUB_SHA
```

---

## Logging & Monitoring

### Structured Logging

```typescript
// src/shared/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label })
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: ['password', 'token', 'authorization']
});

// Usage
logger.info({ orderId, userId }, 'Order created successfully');
logger.error({ error, requestId }, 'Failed to process payment');
```

### Health Check Endpoints

```typescript
// src/api/routes/health.ts
router.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

router.get('/ready', async (req, res) => {
  const checks = {
    database: await checkDatabase(),
    redis: await checkRedis(),
    kafka: await checkKafka()
  };
  
  const healthy = Object.values(checks).every(c => c);
  res.status(healthy ? 200 : 503).json({ ready: healthy, checks });
});
```

---

## Security Best Practices

### Input Validation

```typescript
// Always validate and sanitize input
import { z } from 'zod';

const CreateOrderSchema = z.object({
  addressId: z.string().uuid(),
  items: z.array(z.object({
    variantId: z.string().uuid(),
    quantity: z.number().int().min(1).max(100)
  })).min(1),
  couponCode: z.string().optional(),
  paymentMethod: z.enum(['card', 'upi', 'netbanking', 'cod'])
});
```

### Authentication Middleware

```typescript
// src/api/middleware/auth.ts
export const authenticate = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  if (!token) {
    throw new UnauthorizedError('No token provided');
  }
  
  try {
    const payload = await verifyJWT(token);
    req.user = payload;
    next();
  } catch (error) {
    throw new UnauthorizedError('Invalid token');
  }
};
```

---

## Performance Guidelines

1. **Use connection pooling** for database connections
2. **Implement caching** with Redis for hot data
3. **Use pagination** for list endpoints
4. **Compress responses** with gzip/brotli
5. **Optimize database queries** with proper indexes
6. **Use async/await** properly to avoid blocking
7. **Implement circuit breakers** for external services
8. **Monitor and set alerts** for response times
