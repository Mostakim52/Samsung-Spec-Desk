import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chatbot.chatbot import Chatbot
from database import db
from scraper.gsmarena import load_fallback_dataset
from scraper.models import PhoneRecord

load_dotenv()

CHATBOT: Chatbot | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CHATBOT
    db.init_db()
    if db.count_phones() == 0:
        for record in load_fallback_dataset():
            db.upsert_phone(record)
    CHATBOT = Chatbot()
    yield


app = FastAPI(title="Samsung Phone Query and Review System", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


class AskBody(BaseModel):
    query: str


class ReviewBody(BaseModel):
    phone: str


@app.get("/")
def index():
    path = os.path.join(_static_dir, "index.html")
    return FileResponse(path)


@app.get("/api/phones")
def list_phones():
    return [_phone_payload(p) for p in db.get_all_phones()]


@app.get("/api/phones/{name}")
def get_phone(name: str):
    record = db.get_phone_by_name(name)
    if record is None:
        raise HTTPException(status_code=404, detail="Phone not found")
    return _phone_payload(record)


@app.post("/api/ask")
def ask(body: AskBody):
    result = CHATBOT.ask(body.query)
    return {"answer": result["answer"], "sources": result["sources"]}


@app.post("/api/review")
def review(body: ReviewBody):
    from agents.crew import generate_review

    try:
        return generate_review(body.phone)
    except LookupError:
        raise HTTPException(status_code=404, detail="Phone not found")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent pipeline error: {exc}")


def _phone_payload(record: PhoneRecord) -> dict:
    data = record.__dict__.copy()
    data["raw_specs"] = record.raw_specs
    return data
