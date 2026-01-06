# Documentation: External API Key System (GPT-Style)

This document provides a comprehensive overview of the modular API Key system implemented for the Blog Generation Backend. This system allows external products (like WordPress, mobile apps, or other services) to securely fetch blog content without requiring a human-based Clerk login.

---

## 1. High-Level Architecture
The system is built as a **Shared Module** (`management_app.shared`). This design is "Senior Level" because it is decoupled from the specific `blog_generator` logic, allowing the API Key system to be reused for any other product in the future without duplicating code.

### Components:
- **`shared` App**: A central repository for utilities used across multiple backend modules.
- **Secure Model**: Uses a "Prefix + Hash" pattern for keys (Industry standard used by OpenAI/Stripe).
- **Custom Auth Suite**: A dedicated authentication backend that handles machine-to-machine requests.

---

## 2. Technical Workflow

### Step A: Key Creation (The Admin/Developer Flow)
1. **Generation**: A unique `prefix` (public) and a long `secret_key` (private) are generated.
2. **Storage**: The backend stores only the `prefix` and a **salted hash** of the secret key. Even if the database is leaked, your actual API keys remain safe.
3. **Identity**: Every key is linked to an `organization_name`, ensuring total data isolation.

### Step B: The Handshake (The Integration Flow)
1. An external app sends a request to `/api/external/v1/blogs/`.
2. It includes the key in the header: `X-API-Key: prefix.secret_key`.
3. The **Clerk Middleware** automatically detects correctly that this is an "External" path and steps aside.
4. The `ExternalAPIKeyAuthentication` class validates the key, identifies the organization (e.g., "sooqsense"), and authorizes the request.

### Step C: Data Delivery (The Result Flow)
1. The system fetches only the **Published** blogs for that organization.
2. The `ExternalBlogSerializer` transforms the complex database fields into the exact, clean JSON format requested for external consumption.

---

## 3. How to Use & Test

### Creating a Key (CLI)
Run the following command in your terminal for manual management:
```bash
docker-compose --profile development exec web python manage.py generate_api_key "Product Name" "Organization Name"
```

### Creating a Key (API)
Authenticated users can generate keys via the dashboard using this endpoint:
- **Endpoint**: `POST /api/external/v1/keys/generate/`
- **Auth**: Clerk JWT required.
- **Payload**: `{"name": "Integration Name"}`
- **Security**: Returns the raw secret key **once**.

### Fetching Blogs (Integration Example)
Your other products should simply call these endpoints with the key in the header:

**List Blogs:**
`GET /api/external/v1/blogs/`

**Get Specific Blog:**
`GET /api/external/v1/blogs/<id_or_slug>/`

**Example Header:**
```http
X-API-Key: a9KRa6qrAPs.AsggYILtyZs73NhVStfnIEB1...
```

---

## 4. Key Files & Their Roles

| File path | Purpose |
| :--- | :--- |
| `management_app/shared/models.py` | Defines `BlogAPIKey` with secure hashing storage. |
| `management_app/shared/services/authentication/api_key_auth.py` | The "Security Brain" that verifies keys and handles hashing. |
| `management_app/shared/serializers/external_blog_serializers.py` | Formats output to match the "Example Formate" JSON. |
| `management_app/shared/views.py` | The endpoints that fetch and deliver the blog content. |
| `management_app/authentication/middleware.py` | Configured to allow "External" paths to bypass Clerk Login. |

---

## 5. Security & Efficiency Features
- **Zero Dead Code**: Every function implemented serves a direct purpose in the auth or delivery chain.
- **Production Grade**: Uses Django's `make_password` and `check_password` for cryptographic security.
- **High Performance**: Uses database indexing on prefixes and organization names for near-instant retrieval.
- **Format Flexibility**: Includes on-the-fly Markdown-to-HTML conversion so your external apps don't have to handle formatting.
