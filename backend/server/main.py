from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

from server.api.router import router

load_dotenv()
debug_agent_events = os.getenv("WORKMATE_BACKEND_MODE") == "development" or os.getenv("WORKMATE_AGENT_DEBUG") == "1"
workmate_logger = logging.getLogger("workmate")
workmate_logger.setLevel(logging.INFO if debug_agent_events else logging.WARNING)
if not workmate_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    workmate_logger.addHandler(handler)
    workmate_logger.propagate = False

app = FastAPI(title="workMate API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "null"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "workMate"}
