# CareerLens

> AI-powered resume analyzer. Upload your resume and a job description — get a match score, keyword gap analysis, and a personalized cover letter in seconds.

**Live demo:** [careerlens-one.vercel.app](https://careerlens-one.vercel.app)
**API docs:** [valiant-transformation-production-32e3.up.railway.app/docs](https://valiant-transformation-production-32e3.up.railway.app/docs)

![Tests](https://github.com/MisbahShahzeen/careerlens/actions/workflows/test.yml/badge.svg)

---

## What it does

CareerLens helps job seekers tailor their resume for specific roles. Upload a PDF or DOCX resume, paste a job description, and the app uses Google Gemini to produce:

- A **match score** (0–100) measuring how well the resume fits the role
- **Matched keywords** — skills present in both resume and job description
- **Missing keywords** — important skills from the JD missing from the resume
- **Strengths and improvement suggestions** specific to the role
- A **personalized cover letter** generated from the resume and the job description

Every analysis is saved per user, so candidates can build a history of how their resume scores against different roles.

## Explainable Matching with RAG

CareerLens includes a Retrieval-Augmented Generation (RAG) pipeline that makes job-description matching **explainable** rather than a black-box score.

**The problem with naive prompt stuffing:** The standard approach sends the entire resume and job description to the LLM in one prompt and asks for a score. This truncates long resumes (cutting off content past a character limit), gives no evidence for why a score was assigned, and does surface-level keyword matching.

**The RAG approach:** Instead of one big prompt, CareerLens:

1. **Chunks** the resume into semantic sections (summary, experience, skills, education) and the job description into individual requirements.
2. **Embeds** each chunk into a 768-dimensional vector using Gemini's `gemini-embedding-001` model.
3. **Stores** the embeddings in PostgreSQL using the `pgvector` extension.
4. **Retrieves** the most relevant resume sections for each requirement via cosine similarity search.
5. **Scores** each requirement individually, sending the LLM only the relevant evidence.
6. **Explains** every score with the specific resume chunk that supports it and a similarity percentage.

The result: each job requirement gets its own score, backed by a cited resume section and a strong/weak evidence flag. When a requirement has no supporting evidence (e.g. a skill the candidate lacks), the system honestly flags it as weak rather than hallucinating a match.

### RAG Architecture

```
Resume text                          Job description
     │                                     │
     ▼                                     ▼
Section chunking                    Requirement chunking
     │                                     │
     ▼                                     ▼
Gemini embeddings (768-dim)         Gemini embeddings (768-dim)
     │                                     │
     ▼                                     ▼
Store in pgvector          For each requirement:
                              cosine similarity search
                                     │
                                     ▼
                           Top-K matching chunks
                                     │
                                     ▼
                           LLM scores requirement
                           with cited evidence
                                     │
                                     ▼
                           Aggregate + explanation trail
```

### RAG Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analysis/analyze-rag` | Full RAG pipeline: chunk, embed, retrieve, score |
| GET | `/analysis/{id}/evidence` | Retrieve the evidence trail for a past analysis |
| POST | `/analysis/compare` | Run both prompt-stuffing and RAG side by side |

### Key Design Decisions

- **pgvector over a dedicated vector DB** (Pinecone, Weaviate): the app already runs PostgreSQL, so pgvector adds semantic search with zero extra infrastructure.
- **768 dimensions via Matryoshka truncation**: `gemini-embedding-001` returns 3072 dimensions by default; truncating to 768 balances storage cost against retrieval quality with minimal loss.
- **Cosine similarity threshold of 0.65**: validated empirically — semantically equivalent phrasings ("built REST APIs" vs "developed RESTful services") score ~0.86, while unrelated text scores ~0.49, so 0.65 cleanly separates strong from weak evidence.
- **Retry with exponential backoff**: RAG makes one LLM call per requirement, so transient 503s are handled with retries rather than failing the whole analysis.


## Screenshots

| | |
|---|---|
| ![Login](docs/screenshots/login.png) | ![Analyze](docs/screenshots/analyze.png) |
| Login | Resume + job description upload |
| ![Analysis](docs/screenshots/analysis.png) | ![Cover letter](docs/screenshots/coverletter.png) |
| AI analysis with match score and keywords | AI-generated cover letter |
| ![Dashboard](docs/screenshots/dashboard.png) | |
| User dashboard with analysis history | |

## Tech stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 15 |
| AI | Google Gemini API (`gemini-2.5-flash`) |
| Auth | JWT (python-jose) + bcrypt |
| Infra | Docker (Postgres), Railway (backend + DB), Vercel (frontend) |
| Testing | pytest, FastAPI TestClient |
| CI | GitHub Actions |

## Architecture

```
Browser
  │
  ▼
Next.js frontend  (Vercel)
  │  REST API + JWT bearer token
  ▼
FastAPI backend  (Railway)
  ├── PostgreSQL — users, analyses
  ├── PyPDF2 / python-docx — resume text extraction
  └── Google Gemini API — analysis + cover letter generation
```

## API

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | Create user account | No |
| POST | `/auth/login` | Returns JWT access token | No |
| POST | `/analysis/analyze` | Upload resume + JD → analysis | Yes |
| GET | `/analysis/history` | List user's past analyses | Yes |
| GET | `/analysis/{id}` | Get one analysis by ID | Yes |
| POST | `/analysis/cover-letter/{id}` | Generate cover letter | Yes |

All protected endpoints require an `Authorization: Bearer <token>` header.

## Running locally

**Prerequisites:** Python 3.11+, Node.js 20+, Docker.

```bash
git clone https://github.com/MisbahShahzeen/careerlens
cd careerlens

# Start Postgres in Docker
docker-compose up -d

# Backend setup
cd backend
python -m venv venv
source venv/Scripts/activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
# Create .env with DATABASE_URL, SECRET_KEY, GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload         # runs on http://localhost:8000

# Frontend setup (in another terminal)
cd ../frontend
npm install
# Create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                            # runs on http://localhost:3000
```

### Required environment variables

**Backend (`backend/.env`):**

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/careerlens
SECRET_KEY=random-string
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=your-gemini-api-key
```

**Frontend (`frontend/.env.local`):**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Tests

```bash
cd backend
pytest tests/ -v
```

10 tests cover auth (register, login, duplicate emails, wrong passwords, protected routes) and analysis endpoints (auth required, 404 handling, history). Tests run automatically on every push via GitHub Actions.

## Project structure

```
careerlens/
├── .github/workflows/test.yml      # CI pipeline
├── backend/
│   ├── alembic/                    # Database migrations
│   ├── app/
│   │   ├── core/                   # config, database, security
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── routers/                # Auth + analysis endpoints
│   │   ├── services/               # AI service, PDF/DOCX parser
│   │   └── main.py                 # FastAPI app
│   ├── tests/                      # pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (auth)/                 # Login + signup pages
│   │   ├── analyze/                # Main analysis page
│   │   ├── analysis/[id]/          # Analysis detail page
│   │   └── dashboard/              # User history dashboard
│   └── lib/api.ts                  # Centralized API client
├── docs/screenshots/
└── docker-compose.yml
```

## Author

Built by [Misbah Shahzeen](https://github.com/MisbahShahzeen)