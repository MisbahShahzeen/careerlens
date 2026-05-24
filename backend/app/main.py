from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "CareerLens API is running, hello from misbah"}

@app.get("/health")
def health():
    return {"status": "ok"}