import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db
from auth import router as auth_router
from words import router as words_router
from quiz import router as quiz_router
from progress import router as progress_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LingoDeck API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "lingodeck"}


app.include_router(auth_router)
app.include_router(words_router)
app.include_router(quiz_router)
app.include_router(progress_router)

if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
