# CORE COMMANDS & ARCHITECTURE GUIDELINES

This document is the primary source of truth for all developers and AI agents working on this project.

Failure to follow these rules is considered an architectural violation.

---

# 1. Architecture Style

This project follows a Modular Monolith Architecture with strict layer separation.

Flow:

Route
→ Service
→ Repository
→ Database

Rules:

* Routes must never contain business logic.
* Services contain all business logic.
* Repositories contain all database access.
* Models contain ORM definitions only.
* Schemas contain validation and serialization only.

Forbidden:

* SQLAlchemy queries inside routes.
* SQLAlchemy queries inside services.
* Business logic inside repositories.
* Business logic inside schemas.
* Business logic inside models.

---

# 2. Directory Structure

API Endpoints:

app/api/v1/routes/

Business Modules:

app/modules/{module_name}/

Every module must contain:

models.py
schemas.py
repository.py
constants.py
service/

Example:

app/modules/products/

Rules:

* service.py is prohibited.
* Services must be organized as a package.

Correct:

service/
├── product_service.py
├── pricing_service.py
└── inventory_service.py

Incorrect:

service.py

---

# 3. Service Layer Rules

A service file should focus on one responsibility.

Maximum recommended size:

300-500 lines.

If a service grows larger:

Split it into additional services.

Example:

service/
├── order_service.py
├── payment_service.py
├── discount_service.py
└── carbon_service.py

Service orchestration is allowed.

Service-to-service communication is allowed.

Repository-to-repository communication is prohibited.

---

# 4. Repository Rules

Repositories are responsible only for data access.

Allowed:

* SELECT
* INSERT
* UPDATE
* DELETE

Forbidden:

* Permission validation
* Business calculations
* Pricing logic
* Token generation
* External API calls

Repositories must be stateless.

---

# 5. Authentication & Authorization

Authentication is centralized inside:

app/modules/auth/

Use:

Depends(get_current_user)

for authenticated endpoints.

Use:

Depends(require_roles(...))

for RBAC.

Never hardcode roles inside routes.

Never hardcode company or store ownership checks inside routes.

Ownership validation belongs to services.

---

# 6. Database & Alembic

Whenever models change:

1. Generate migration.
2. Review migration.
3. Apply migration.

Commands:

alembic revision --autogenerate -m "description"

alembic upgrade head

Never modify production schema manually.

---

# 7. Pagination Standard

All list endpoints must support:

page
page_size

Response:

{
"items": [],
"pagination": {
"page": 1,
"page_size": 20,
"total": 100,
"total_pages": 5
}
}

Pagination calculations belong to services.

---

# 8. Storage Layer

All file handling must go through:

app/storage/

Forbidden:

* Direct filesystem operations inside routes.
* Direct filesystem operations inside services.

Use:

StorageProvider interface.

Supported providers:

* Local Storage
* S3
* MinIO

Services must depend on StorageProvider abstraction.

Never depend directly on S3 SDKs.

---

# 9. AI Provider Layer

All LLM integrations must go through:

app/ai/

Services must never call DeepSeek directly.

Correct:

Service
→ AI Factory
→ Provider

Incorrect:

Service
→ DeepSeek API

Providers must implement:

LLMProvider interface.

Supported providers:

* DeepSeek
* OpenAI
* Anthropic

Future providers must be interchangeable.

---

# 10. MCP Architecture

All tools belong to:

app/mcp/tools/

Every MCP tool must inherit:

BaseTool

Every tool must expose:

* schema
* execute()

Tool registration belongs to:

app/mcp/registry.py

Tool execution belongs to:

app/mcp/orchestrator.py

Chat services must never call tools directly.

Correct:

Chat Service
→ MCP Orchestrator
→ Tool

Incorrect:

Chat Service
→ Tool

---

# 11. Chat Module

Chat functionality belongs to:

app/modules/chat/

Responsibilities:

* Conversation Management
* Context Management
* Tool Calling
* Memory Management
* Response Generation

Chat services must not contain provider-specific logic.

Provider logic belongs to:

app/ai/providers/

---

# 12. Logging

Use structured logging.

Never use:

print()

Use:

logger.info()
logger.warning()
logger.error()

---

# 13. Configuration

Environment variables must be accessed through:

app/core/config.py

Never call:

os.getenv()

throughout the codebase.

Use centralized settings.

---

# 14. Testing

Every new feature should include:

* Service tests
* Repository tests

Business logic must be tested at service level.

---

# 15. Code Quality

Prefer composition over inheritance.

Prefer explicit types.

Avoid utility classes.

Avoid god services.

Avoid god repositories.

Keep files focused on a single responsibility.

Every feature must preserve architectural consistency.
