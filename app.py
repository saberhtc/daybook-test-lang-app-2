import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import init_db
from auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LingoDeck", lifespan=lifespan)

app.include_router(auth_router)

if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
