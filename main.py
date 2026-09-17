from dotenv import load_dotenv
from fastapi import FastAPI

from src.routes import router

load_dotenv()

app = FastAPI(title="APITest Orchestrator Python Middleware")
app.include_router(router)
