from chatbot.retriever import Retriever
from scraper import gsmarena


def _retriever():
    return Retriever(gsmarena.load_fallback_dataset())


def test_resolve_exact_name():
    r = _retriever()
    assert [p.name for p in r.resolve_mentions("Galaxy S23")] == ["Galaxy S23"]


def test_resolve_short_model():
    r = _retriever()
    assert [p.name for p in r.resolve_mentions("s23 ultra")] == ["Galaxy S23 Ultra"]


def test_resolve_multi_mentions():
    r = _retriever()
    names = [p.name for p in r.resolve_mentions("s23 vs s22 ultra")]
    assert "Galaxy S23" in names and any(
        n.startswith("Galaxy S22 Ultra") for n in names
    )


def test_no_mentions():
    assert _retriever().resolve_mentions("hello there") == []


def test_best_battery():
    r = _retriever()
    ctx, sources = r.retrieve("Which Samsung phone has the best battery life?")
    assert "battery" in ctx.lower()
    assert len(sources) >= 3


def test_semantic_offline():
    import chatbot.retriever as mod
    mod.Chroma = None
    r = _retriever()
    ctx, sources = r.retrieve("tell me about the foldable phones")
    assert isinstance(ctx, str) and isinstance(sources, list)
