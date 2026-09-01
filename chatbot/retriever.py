import re

from scraper.models import PhoneRecord

try:
    from chromadb import PersistentClient
    from sentence_transformers import SentenceTransformer
    Chroma = True
except ImportError:
    Chroma = None

_BATTERY_RE = re.compile(r"best\s+(battery|battery life)", re.I)
_COMPARE_RE = re.compile(r"\b(vs\.?|versus|compare|comparison|better)\b", re.I)
_BEST_RE = re.compile(r"best\s+(battery|battery life|camera|display|performance|processor)", re.I)
_SEGMENT_SPLIT = re.compile(r"\b(vs\.?|versus|compare(d)? (to|with)|against|and)\b", re.I)
_NOISE_TOKENS = {"galaxy", "samsung", "5g", "4g"}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("+", " plus "))


def _is_separator(text: str) -> bool:
    return bool(_SEGMENT_SPLIT.fullmatch(text.strip()))


def is_best_of(query: str) -> bool:
    return bool(_BATTERY_RE.search(query) or _BEST_RE.search(query))


def is_comparison(query: str) -> bool:
    return bool(_COMPARE_RE.search(query))


class Retriever:
    def __init__(self, records: list[PhoneRecord]):
        self.records = sorted(records, key=lambda r: r.name)
        self._chroma = None
        self._model = None

    def resolve_mentions(self, query: str) -> list[PhoneRecord]:
        segments = self._split_segments(query)
        hits, seen = [], set()
        for segment in segments:
            tokens = set(_normalize(segment).split())
            segment_hits = []
            for record in self.records:
                name_tokens = [
                    t for t in _normalize(record.name).split()
                    if t not in _NOISE_TOKENS
                ]
                if not name_tokens:
                    continue
                if all(t in tokens for t in name_tokens):
                    if record.name not in seen:
                        segment_hits.append(record)
                        seen.add(record.name)
            hits.extend(self._drop_subsets(segment_hits))
        return hits

    @staticmethod
    def _split_segments(query: str) -> list[str]:
        words = query.split()
        segments, current = [], []
        for word in words:
            if _is_separator(word):
                segments.append(" ".join(current))
                current = []
            else:
                current.append(word)
        segments.append(" ".join(current))
        return [s for s in segments if s] or [query]

    @staticmethod
    def _drop_subsets(hits: list[PhoneRecord]) -> list[PhoneRecord]:
        sets = {
            id(r): {
                t for t in _normalize(r.name).split() if t not in _NOISE_TOKENS
            }
            for r in hits
        }
        kept = []
        for record in hits:
            record_set = sets[id(record)]
            if any(
                record_set < sets[id(other)] for other in hits if other is not record
            ):
                continue
            kept.append(record)
        return kept

    def _ensure_index(self):
        if self._chroma is not None or Chroma is None:
            return
        client = PersistentClient(path="./chroma_store")
        collection = client.get_or_create_collection("phones")
        if collection.count() != len(self.records):
            if collection.count():
                client.delete_collection("phones")
                collection = client.get_or_create_collection("phones")
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            for i, record in enumerate(self.records):
                collection.add(ids=[str(i)], documents=[record.to_doc()])
        self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self._chroma = collection

    def semantic_search(self, query: str, k: int = 3) -> list[PhoneRecord]:
        self._ensure_index()
        if self._chroma is None:
            return self.records[:k]
        emb = self._model.encode([query]).tolist()
        result = self._chroma.query(query_embeddings=emb, n_results=min(k, len(self.records)))
        return [self.records[int(i)] for i in result["ids"][0]]

    def retrieve(self, query: str) -> tuple[str, list[PhoneRecord]]:
        mentioned = self.resolve_mentions(query)
        if is_comparison(query) or is_best_of(query):
            records = mentioned if mentioned else self.records[:8]
        else:
            records = mentioned if mentioned else self.semantic_search(query)
        if not records:
            records = self.records[:3]
        context = "\n\n".join(r.to_doc() for r in records)
        return context, records
