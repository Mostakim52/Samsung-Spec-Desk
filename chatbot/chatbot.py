import os
from typing import Optional

from dotenv import load_dotenv

from chatbot.retriever import Retriever
from scraper.models import PhoneRecord

load_dotenv()

SYSTEM_PROMPT = (
    "You answer questions about Samsung smartphones using ONLY the provided phone "
    "spec sheets. Be concise and factual. Quote exact numbers. If the phone is not "
    "in the provided sheets, say you don't have data on it. Never invent specs."
)

GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "groq/compound-mini",
]


class Chatbot:
    def __init__(self, records: Optional[list[PhoneRecord]] = None):
        if records is None:
            import database.db as db
            records = db.get_all_phones()
            if not records:
                from scraper.gsmarena import load_fallback_dataset
                records = load_fallback_dataset()
        self.retriever = Retriever(records)
        self._client = None
        self._model = None
        self._limits = {}
        key = os.getenv("GROQ_API_KEY", "")
        self._llm_available = bool(key and key != "your_groq_api_key_here")

    def _groq_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
            )
        return self._client

    def _pick_model(self) -> str:
        if self._model:
            return self._model
        client = self._groq_client()
        self._limits = {}
        try:
            for m in client.models.list():
                limit = getattr(m, "max_completion_tokens", None)
                if limit:
                    self._limits[m.id] = int(limit)
        except Exception:
            pass
        available = set(self._limits) or None
        for model in GROQ_MODELS:
            if available is None or model in available:
                self._model = model
                return model
        if available:
            chat_models = [
                m for m in available
                if "whisper" not in m and "guard" not in m and "orpheus" not in m
            ]
            self._model = sorted(chat_models)[0] if chat_models else sorted(available)[0]
        else:
            self._model = GROQ_MODELS[0]
        return self._model

    def _max_tokens(self) -> int:
        limit = self._limits.get(self._model, 512)
        return min(400, limit)

    def ask(self, query: str) -> dict:
        context, sources = self.retriever.retrieve(query)
        if not self._llm_available:
            answer = (
                "Generative mode is off (no GROQ_API_KEY). "
                "Retrieved spec sheets:\n\n" + context
            )
            return {"answer": answer, "sources": [r.name for r in sources]}
        try:
            client = self._groq_client()
            response = client.chat.completions.create(
                model=self._pick_model(),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
                ],
                temperature=0.2,
                max_tokens=self._max_tokens(),
            )
            answer = response.choices[0].message.content.strip()
            return {"answer": answer, "sources": [r.name for r in sources]}
        except Exception as exc:
            return {"answer": f"LLM error: {exc}", "sources": [r.name for r in sources]}
