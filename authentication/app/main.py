from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.auth.clients.database import engine, Base
from app.auth.router import router as auth_router
from app.users.router import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    Base.metadata.create_all(bind=engine)

    yield
    # shutdown

app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(user_router)