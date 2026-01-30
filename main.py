from fastapi import FastAPI, HTTPException
from models import UserCreate, PostCreate
import asyncio
from contextlib import asynccontextmanager
from database import connect_to_mongo, close_mongo_connection, get_database
from System import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await connect_to_mongo()
    yield
    await close_mongo_connection()
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
