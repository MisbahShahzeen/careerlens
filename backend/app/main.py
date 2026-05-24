from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, analysis

app = FastAPI(title="CareerLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analysis.router)

@app.get("/")
def home():
    return {"message": "CareerLens API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}