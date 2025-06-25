# Alter8 Auth Service

JWT-based authentication service with multi-role support for the Alter8 platform.

## Features

- 🔐 **JWT Authentication** - Secure token-based authentication with refresh tokens
- 👥 **Multi-Role Support** - Agent, Customer, Field Executive, Owner, Admin roles
- 📱 **OTP Verification** - WhatsApp, SMS, and Email OTP support
- 🔒 **RBAC** - Role-based access control with granular permissions
- 🚀 **High Performance** - Async FastAPI with Redis caching
- 📊 **Monitoring** - Prometheus metrics and structured logging
- 🔧 **Modern Tools** - Built with latest Python tools (uv, ruff, mypy)

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for package management
- Docker & Docker Compose
- PostgreSQL and Redis (via Docker)

### Setup

1. **Install dependencies**:
   ```bash
   python setup.py
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start databases**:
   ```bash
   cd ../../  # Go to project root
   docker-compose up postgres redis -d
   ```

4. **Run migrations**:
   ```bash
   uv run alembic upgrade head
   ```

5. **Start the service**:
   ```bash
   uv run uvicorn app.main:app --reload --port 8001
   ```

6. **Access the API**:
   - API Docs: http://localhost:8001/docs
   - Health Check: http://localhost:8001/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/agent` - Agent registration
- `POST /api/v1/auth/register/customer` - Customer registration  
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout

### OTP Verification
- `POST /api/v1/otp/send` - Send OTP
- `POST /api/v1/otp/verify` - Verify OTP
- `POST /api/v1/otp/customer-access` - Customer property access

### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `POST /api/v1/users/change-password` - Change password

### Admin
- `POST /api/v1/admin/users/field-executive` - Create field executive
- `POST /api/v1/admin/users/approve` - Approve/reject user
- `GET /api/v1/admin/users` - List users with filters

## User Roles & Permissions

### Agent
- Register with agency details and RERA license
- Create and manage property listings
- Share properties with customers
- Manage leads and contacts

### Customer  
- Register via OTP (no password required)
- Access shared properties via WhatsApp OTP
- Shortlist properties for visits
- Search and filter properties

### Field Executive
- Created by admin with assigned credentials
- Verify and update property details
- Submit verification reports with media

### Admin
- Create and manage field executive accounts
- Approve/reject agent registrations
- System configuration and monitoring

## Development

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type checking
uv run mypy app

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/auth_db

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

## Architecture

```
app/
├── api/v1/           # API endpoints
├── core/             # Core functionality
│   ├── config.py     # Configuration
│   ├── database.py   # Database setup
│   ├── security.py   # JWT & password utils
│   └── redis_client.py # Redis operations
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── main.py          # FastAPI app
```

## Monitoring

- **Health Check**: `/health`
- **Metrics**: `/metrics` (Prometheus format)
- **Logs**: Structured JSON logs via structlog
- **Tracing**: Request ID tracking

## Security Features

- Password strength validation
- Account lockout after failed attempts
- Rate limiting per IP/user
- JWT token validation and refresh
- OTP expiration and attempt limits
- Audit logging for security events

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_auth.py

# Run with verbose output
uv run pytest -v
```

## Deployment

### Docker

```bash
# Build image
docker build -t alter8-auth-service .

# Run container
docker run -p 8001:8001 alter8-auth-service
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/
```

## Support

For issues and questions:
- 📧 Email: dev@alter8residential.com
- 📖 Documentation: `/docs`
- 🔧 Health Check: `/health`