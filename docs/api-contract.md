# AI Financial Research Assistant — API Contract

**Status:** Finalized (pre–Milestone 2 design)

---

## Conventions

1. **Versioned paths**: `/api/v1/...` for user-facing (browser → Spring Boot), `/internal/v1/...` for service-to-service (Spring Boot ↔ Python). Internal paths are blocked from public internet at the Nginx/firewall level and secured with a shared service token, not a user JWT.
2. **No response envelope.** Plain REST resources + proper HTTP status codes (200/201/404/422). Paginated endpoints use Spring Data's default `Page<T>` shape: `{ content: [...], page, size, totalElements }`.
3. **Consistent error shape:**
```json
{ "timestamp": "2026-07-03T10:15:00Z", "status": 404, "error": "NOT_FOUND", "message": "Document not found", "path": "/api/v1/documents/42" }
```
4. **Status polling is a dedicated lightweight endpoint** (`GET /documents/{id}/status`), separate from the full document resource — cheap to poll every few seconds.
5. **Chat Q&A is `POST /chats/{id}/messages`**, not a separate `/ask` RPC-style endpoint — a question is just a message resource being created, keeping the model RESTful.

---

## Public API — `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Returns access + refresh token |
| POST | `/auth/refresh` | Exchange refresh token for new access token |
| POST | `/auth/logout` | Invalidate refresh token |
| GET | `/users/me` | Current user profile |
| PUT | `/users/me` | Update profile |
| GET | `/companies?search=` | List / search companies |
| GET | `/companies/{id}` | Company detail |
| GET | `/companies/{id}/metrics/trend?metric=revenue` | Time-series for charts |
| POST | `/documents` | Upload (multipart) → returns `UPLOADED` doc |
| GET | `/documents?companyId=&status=&page=` | List (paginated, filterable) |
| GET | `/documents/{id}` | Full document detail |
| GET | `/documents/{id}/status` | Lightweight poll target |
| DELETE | `/documents/{id}` | Remove document + its chunks/vectors |
| GET | `/documents/{id}/financial-statements` | Extracted statements |
| GET | `/documents/{id}/financial-metrics` | Computed ratios |
| GET | `/documents/{id}/insights?type=SWOT` | AI-generated SWOT / summary / risks |
| POST | `/chats` | Start a new conversation |
| GET | `/chats` | List user's chats |
| PUT | `/chats/{id}` | Rename |
| DELETE | `/chats/{id}` | Delete |
| GET | `/chats/{id}/messages` | Conversation history |
| POST | `/chats/{id}/messages` | Ask a question → triggers RAG, returns AI message + citations |
| POST | `/bookmarks` | Bookmark a document/company |
| GET | `/bookmarks` | List bookmarks |
| DELETE | `/bookmarks/{id}` | Remove |
| GET | `/search?q=&type=company,document,chat` | Global search |
| GET | `/dashboard` | Recent uploads, chats, favorites, stats |
| GET | `/notifications` | List |
| PUT | `/notifications/{id}/read` | Mark read |

## Internal API — `/internal/v1` (service-token auth, not user JWT)

| Method | Path | Direction | Purpose |
|---|---|---|---|
| POST | `/process` | Spring → Python | Kick off extraction/chunking/embedding |
| PUT | `/documents/{id}/status` | Python → Spring | Report progress/failure |
| POST | `/query` | Spring → Python | RAG: question + doc scope → answer + citations |
| POST | `/insights` | Spring → Python | Generate SWOT/summary/risk analysis |

---

## Key payload shapes

**`POST /documents`** → response
```json
{
  "id": 42,
  "fileName": "reliance_annual_2024.pdf",
  "companyId": 7,
  "documentType": "ANNUAL_REPORT",
  "status": "UPLOADED",
  "uploadedAt": "2026-07-03T10:00:00Z"
}
```

**`GET /documents/{id}/status`**
```json
{ "status": "EMBEDDING", "progressMessage": "Generating embeddings (320/480 chunks)" }
```

**`POST /chats/{id}/messages`** request

First message — associate documents with the chat:
```json
{ "content": "What was the revenue growth in FY2024?", "documentIds": [42] }
```

Subsequent messages — documents are resolved automatically from chat's persisted association:
```json
{ "content": "What about net income?" }
```

> `documentIds` is optional. If provided, those documents are **persistently associated** with the chat.
> On subsequent requests, if `documentIds` is omitted or empty, the backend automatically resolves
> the chat's previously associated documents. The client does not need to resend document IDs.

response
```json
{
  "id": 501,
  "role": "ASSISTANT",
  "content": "Revenue grew 14% year-over-year, driven primarily by the retail segment.",
  "citations": [
    { "documentId": 42, "documentName": "reliance_annual_2024.pdf", "page": 32 }
  ],
  "createdAt": "2026-07-03T10:05:00Z"
}
```

**Internal `POST /internal/v1/process`** request
```json
{ "documentId": 42, "filePath": "/data/uploads/42.pdf", "fileType": "PDF" }
```
response
```json
{ "accepted": true }
```

**Internal `PUT /internal/v1/documents/{id}/status`** request
```json
{ "status": "READY" }
```
```json
{ "status": "FAILED", "errorMessage": "Unable to parse PDF: corrupted file" }
```

**Internal `POST /internal/v1/query`** request
```json
{ "question": "What was the revenue growth in FY2024?", "documentIds": [42] }
```
response
```json
{
  "answer": "Revenue grew 14% year-over-year, driven primarily by the retail segment.",
  "citations": [ { "documentId": 42, "chunkId": 918, "page": 32 } ]
}
```

## Open items

- [ ] Folder structure for all 3 services
- [ ] Milestone 2: Spring Boot project setup (first real code)
