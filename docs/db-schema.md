# AI Financial Research Assistant — Database Schema (ERD)

**Status:** Finalized (pre–Milestone 2 design)

---

## Design decisions

1. **Companies are first-class**, separate from Documents. One company has many documents over time (Q1, Q2, Annual Reports across years) — required for cross-document trend charts and "favorite companies."
2. **Vectors live in FAISS; chunk metadata lives in Postgres.** `document_chunks.vector_id` is the bridge — same integer used as the FAISS index id. This join is what makes citations (`"Annual Report, Page 32"`) possible.
3. **Citations are their own table** (`message_citations`), not a text blob on the message — one row per cited chunk, enabling clickable/verifiable citations.
4. **Financial statements and metrics are split** — a statement (e.g. "Income Statement, FY2024") can produce many metrics (ROE, Net Margin, etc.) without needing schema changes when new ratios are added.
5. **Bookmarks are polymorphic** (`target_type` + `target_id`) so one table covers bookmarking both documents and companies.

---

## ER Diagram

```
┌──────────────┐         ┌───────────────────┐
│    users      │         │    companies        │
│──────────────│         │───────────────────│
│ id (PK)       │         │ id (PK)             │
│ email         │         │ name                 │
│ password_hash │         │ ticker_symbol         │
│ full_name     │         │ sector                │
│ created_at    │         │ created_at            │
└──────┬───────┘         └─────────┬─────────┘
       │ 1                          │ 1
       │ *                          │ *
┌──────▼───────────┐        ┌───────▼──────────────┐
│  refresh_tokens    │       │      documents          │
│───────────────────│       │─────────────────────────│
│ id (PK)             │      │ id (PK)                   │
│ user_id (FK)         │     │ company_id (FK)             │
│ token                │      │ uploaded_by (FK -> users)    │
│ expires_at           │      │ file_name                    │
└────────────────────┘       │ file_type (PDF/DOCX/TXT)      │
                              │ file_size                      │
       ┌──────────────────┐  │ document_type (ANNUAL/QTR/...) │
       │    bookmarks        │  │ status (UPLOADED/EXTRACTING/  │
       │────────────────────│  │   CHUNKING/EMBEDDING/READY/   │
       │ id (PK)              │  │   FAILED)                     │
       │ user_id (FK)          │  │ fiscal_year                   │
       │ target_type            │  │ uploaded_at                    │
       │  (DOCUMENT/COMPANY)     │  └──────────┬─────────────────────┘
       │ target_id                │             │ 1
       │ created_at                 │            │
       └────────────────────────┘              │ *
                                     ┌──────────▼──────────────┐
                                     │   document_chunks          │
                                     │───────────────────────────│
                                     │ id (PK)                      │
                                     │ document_id (FK)               │
                                     │ chunk_index                     │
                                     │ page_number                       │
                                     │ text_preview                       │
                                     │ vector_id (int, maps to FAISS)      │
                                     └──────────┬──────────────────────────┘
                                                 │ 1
                                                 │ *
┌──────────────┐        ┌──────────────────┐   ┌▼─────────────────────┐
│    chats      │        │   chat_messages    │   │   message_citations     │
│──────────────│        │──────────────────│   │─────────────────────────│
│ id (PK)       │  1   * │ id (PK)            │ 1 │ id (PK)                   │
│ user_id (FK)   │───────►│ chat_id (FK)        │──►│ message_id (FK)            │
│ title          │        │ role (USER/ASSISTANT)│  │ chunk_id (FK)               │
│ company_id (FK,│        │ content              │  │ page_number                  │
│  nullable)      │        │ created_at            │  └──────────────────────────────┘
│ created_at       │       └──────────────────────┘
└──────────────────┘

┌───────────────────────┐        ┌──────────────────────────┐
│  financial_statements     │        │   financial_metrics          │
│───────────────────────────│        │──────────────────────────────│
│ id (PK)                     │  1  * │ id (PK)                        │
│ document_id (FK)              │───────► statement_id (FK)              │
│ statement_type                  │      │ metric_name (e.g. "ROE")       │
│  (INCOME/BALANCE/CASHFLOW)       │     │ metric_value                    │
│ fiscal_year                        │    │ unit (%, ratio, currency)        │
│ period (Q1/Q2/Q3/Q4/FY)              │  └─────────────────────────────────┘
└────────────────────────────────────┘

┌───────────────────────┐
│    notifications          │
│───────────────────────────│
│ id (PK)                     │
│ user_id (FK)                  │
│ message                         │
│ is_read                           │
│ created_at                          │
└─────────────────────────────────────┘
```

## Relationship summary

| Relationship | Type | Why |
|---|---|---|
| `users` → `documents` | 1:* | One user can upload many documents |
| `companies` → `documents` | 1:* | One company has many reports over time |
| `documents` → `document_chunks` | 1:* | One document splits into many chunks |
| `chats` → `chat_messages` | 1:* | One conversation, many turns |
| `chat_messages` → `message_citations` | 1:* | One AI answer can cite multiple chunks |
| `document_chunks` → `message_citations` | 1:* | One chunk can be cited by many messages over time |
| `chats` → `companies` | *:1 (nullable) | A chat can optionally be scoped to one company |
| `financial_statements` → `financial_metrics` | 1:* | One statement produces many computed ratios |
| `users` → `bookmarks` | 1:* | Polymorphic: points at a document OR a company |

## Open items

- [ ] Exact column types and constraints (finalized as JPA `@Entity` classes in Milestone 4)
- [ ] Indexing strategy (e.g. index on `documents.company_id`, `document_chunks.document_id`)
- [ ] API endpoint contracts
- [ ] Folder structure for all 3 services
