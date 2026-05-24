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