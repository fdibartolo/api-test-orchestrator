from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from src.routes import router

app = FastAPI(title="APITest Orchestrator Python Middleware")
app.include_router(router)
