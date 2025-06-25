# Alter8 Platform - Multi-Product Real Estate Platform

## Overview

Alter8 is a comprehensive real estate platform that connects property owners, tenants, real estate agents, and field executives through three primary applications with shared backend services.

### Applications

- **Alter8 Residential** (`alter8residential.com`) - Property owners, tenants, property managers
- **Alter8 Property** (`alter8property.com`) - Real estate agents, brokers, field executives  
- **Alter8 Admin** (`alter8admin.com`) - Platform administrators, super admins

## Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: Python/FastAPI + Node.js/NestJS microservices
- **Databases**: PostgreSQL, MongoDB, Redis
- **Infrastructure**: Google Cloud Platform with Kubernetes

## Project Structure

```
alter8-platform/
├── apps/                    # Frontend Applications
│   ├── alter8-residential/  # Property owners & tenants
│   ├── alter8-property/     # Agents & brokers
│   └── alter8-admin/        # Platform administration
├── services/                # Backend Microservices
│   ├── auth-service/        # Authentication & user management
│   ├── property-service/    # Property CRUD & search
│   ├── agent-service/       # Agent profiles & performance
│   ├── tenant-service/      # Tenant management & KYC
│   ├── lease-service/       # Lease agreements & renewals
│   ├── document-service/    # File management
│   ├── payment-service/     # Payment processing
│   ├── verification-service/ # Property verification workflow
│   ├── analytics-service/   # Business intelligence
│   ├── notification-service/ # Multi-channel notifications
│   ├── contact-service/     # CRM & lead management
│   ├── sharing-service/     # Property sharing
│   ├── maintenance-service/ # Maintenance requests
│   └── api-gateway/         # API routing & security
├── packages/                # Shared Libraries
│   ├── shared-types/        # TypeScript definitions
│   ├── ui-components/       # Shared React components
│   ├── api-client/          # Type-safe API client
│   ├── utils/               # Utility functions
│   └── config/              # Configuration constants
├── infrastructure/          # Infrastructure as Code
│   ├── terraform/           # GCP resource management
│   ├── kubernetes/          # K8s manifests
│   ├── helm-charts/         # Helm deployment charts
│   └── scripts/             # Deployment scripts
├── docs/                    # Documentation
│   ├── api/                 # API documentation
│   ├── architecture/        # Architecture diagrams
│   ├── deployment/          # Deployment guides
│   └── user-guides/         # User documentation
└── tools/                   # Development Tools
    ├── db-migrations/       # Database migration scripts
    ├── data-seeding/        # Test data generation
    └── monitoring/          # Monitoring configurations
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.9+
- Docker & Docker Compose
- Google Cloud SDK

### Development Setup

1. Clone the repository
```bash
git clone <repository-url>
cd alter8-platform
```

2. Install dependencies
```bash
npm install
```

3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start development environment
```bash
docker-compose up -d
```

5. Run database migrations
```bash
npm run migrate
```

6. Start development servers
```bash
npm run dev
```

## Development

### Scripts

- `npm run dev` - Start all services in development mode
- `npm run build` - Build all applications and services
- `npm run test` - Run test suite
- `npm run lint` - Run linting
- `npm run migrate` - Run database migrations
- `npm run seed` - Seed development data

### Testing

- Unit tests: `npm run test:unit`
- Integration tests: `npm run test:integration`
- E2E tests: `npm run test:e2e`

## Deployment

### Staging
```bash
npm run deploy:staging
```

### Production
```bash
npm run deploy:production
```

## Documentation

- [API Documentation](./docs/api/)
- [Architecture Overview](./docs/architecture/)
- [Deployment Guide](./docs/deployment/)
- [User Guides](./docs/user-guides/)

## Contributing

Please read our contributing guidelines and code of conduct before submitting pull requests.

## License

Private - Alter8 Residential