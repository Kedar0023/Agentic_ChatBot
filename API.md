# API Reference

## Authentication (`/v2/auth`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v2/auth/register` | Register new user | `{ "username": "str(3-50)", "password": "str(6-100)" }` | `{ "message": "str", "userId": "str" }` |
| `POST /v2/auth/login` | Authenticate user & set cookie | `{ "username": "str", "password": "str" }` | `{ "message": "str", "userId": "str", "username": "str", "access_token": "str" }` |
| `POST /v2/auth/logout` | Revoke session & clear cookie | Cookie: `refresh_token` | `{ "message": "str" }` |

---

## Session Management (`/v2/session`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v2/session/refresh` | Rotate refresh token & return new access token | Cookie: `refresh_token` | `{ "message": "str", "userId": "str", "username": "str", "access_token": "str" }` |
| `GET /v2/session/me` | Fetch authenticated user profile | Header: `Authorization: Bearer <token>` | `{ "id": "str", "userId": "str", "username": "str", "is_active": true }` |

---

## Chat Threads (`/v2/thread`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v2/thread/create` | Create new chat thread | Header: `Authorization: Bearer <token>` | `{ "thread_id": "str" }` |
| `GET /v2/thread/list_threads` | List all user threads | Header: `Authorization: Bearer <token>` | `[ { "id": "str", "title": "str" } ]` |
| `GET /v2/thread/{thread_id}/messages` | Get message history of a thread | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "messages": [ { "id": "str", "role": "user\|assistant", "content": "str", "status": "str" } ] }` |
| `GET /v2/thread/{thread_id}/models` | Get thread current/available models | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "current_model": "str", "default_model": "str", "models": ["str"] }` |
| `PATCH /v2/thread/{thread_id}/model` | Change thread model | Path: `thread_id`, Header: `Authorization: Bearer <token>`, Body: `{ "model": "str" }` | `{ "thread_id": "str", "model": "str" }` |
| `PATCH /v2/thread/{thread_id}/title` | Update thread title | Path: `thread_id`, Header: `Authorization: Bearer <token>`, Body: `{ "title": "str(1-255)" }` | `{ "thread_id": "str", "title": "str" }` |
| `DELETE /v2/thread/{thread_id}` | Delete thread | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "message": "str", "thread_id": "str" }` |

---

## Chat Streaming (`/v2/chat`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v2/chat/anonymous` | Free unauthenticated SSE chat stream (max 20 msgs) | Body: `{ "prompt": "str", "history": [ { "role": "human\|ai", "content": "str" } ] }` | SSE Stream (`text/event-stream`) |
| `POST /v2/chat/{thread_id}` | Authenticated persistent SSE chat stream | Path: `thread_id`, Header: `Authorization: Bearer <token>`, Body: `{ "prompt": "str", "llm_model"?: "str", "history"?: [...] }` | SSE Stream (`text/event-stream`) |

---

## Documents (`/v2/thread/{thread_id}`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v2/thread/{thread_id}/upload` | Upload document (PDF, TXT, MD, CSV, DOCX <= 20MB) | Path: `thread_id`, Header: `Authorization: Bearer <token>`, Form: `file` | `{ "message": "str" }` |
| `GET /v2/thread/{thread_id}/docs/{document_id}` | Download stored document | Path: `thread_id`, `document_id`, Header: `Authorization: Bearer <token>` | File Stream (`application/octet-stream`) |
| `POST /v2/thread/{thread_id}/docs/{document_id}/ingest` | Chunk, embed & vector-index PDF document | Path: `thread_id`, `document_id`, Header: `Authorization: Bearer <token>` | `{ "message": "str", "document": { "id": "str", "thread_id": "str", "filename": "str", "status": "str", "total_chunks": 0 } }` |

---

## Legacy V1 API (`/v1`)

| Endpoint | Info | Input Schema | Output Schema |
| :--- | :--- | :--- | :--- |
| `POST /v1/auth/register` | V1 Register | `{ "username": "str", "password": "str" }` | `{ "message": "str", "userId": "str" }` |
| `POST /v1/auth/login` | V1 Login | `{ "username": "str", "password": "str" }` | `{ "message": "str", "userId": "str", "username": "str", "access_token": "str" }` |
| `POST /v1/auth/refresh` | V1 Refresh Token | Cookie: `refresh_token` | `{ "message": "str", "userId": "str", "username": "str", "access_token": "str" }` |
| `POST /v1/auth/logout` | V1 Logout | Cookie: `refresh_token` | `{ "message": "str" }` |
| `GET /v1/auth/me` | V1 Get User | Header: `Authorization: Bearer <token>` | `{ "id": "str", "userId": "str", "username": "str", "is_active": true }` |
| `POST /v1/chat/free` | V1 Anonymous SSE Stream | Body: `{ "prompt": "str", "history": [...] }` | SSE Stream (`text/event-stream`) |
| `POST /v1/chat/new_thread` | V1 Create Thread | Header: `Authorization: Bearer <token>` | `{ "thread_id": "str" }` |
| `POST /v1/chat/base/{thread_id}` | V1 Chat Stream | Path: `thread_id`, Header: `Authorization: Bearer <token>`, Body: `{ "prompt": "str" }` | SSE Stream (`text/event-stream`) |
| `GET /v1/chat/base/get_messages/{thread_id}` | V1 Get Messages | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "messages": [...] }` |
| `GET /v1/chat/base/{thread_id}/models` | V1 Get Models | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "current_model": "str", "default_model": "str", "models": ["str"] }` |
| `PATCH /v1/chat/base/{thread_id}/model` | V1 Update Model | Path: `thread_id`, Body: `{ "model": "str" }` | `{ "thread_id": "str", "model": "str" }` |
| `GET /v1/chat/base/get_all_thread_titles` | V1 List Threads | Header: `Authorization: Bearer <token>` | `[ { "id": "str", "title": "str" } ]` |
| `PATCH /v1/chat/base/{thread_id}/title` | V1 Update Title | Path: `thread_id`, Body: `{ "title": "str" }` | `{ "thread_id": "str", "title": "str" }` |
| `DELETE /v1/chat/base/{thread_id}` | V1 Delete Thread | Path: `thread_id`, Header: `Authorization: Bearer <token>` | `{ "message": "str", "thread_id": "str" }` |
| `POST /v1/chat/{thread_id}/documents` | V1 Upload Doc | Path: `thread_id`, Form: `file` | `{ "message": "str" }` |
| `GET /v1/chat/{thread_id}/documents/{document_id}` | V1 Download Doc | Path: `thread_id`, `document_id` | File Stream |
| `POST /v1/chat/{thread_id}/documents/{document_id}/process` | V1 Ingest Doc | Path: `thread_id`, `document_id` | Document processing status |
