"""ClaudeAssessor tests with a fake client: no network, no API key."""

from types import SimpleNamespace

from tranquera.assessors import ClaudeAssessor, Context, build_user_prompt
from tranquera.catalog import control_index
from tranquera.engine import analyze
from tranquera.models import Action, Verdict
from tranquera.retrieval import Retriever

from .conftest import AS_OF


class FakeClient:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        answer = self.answer(kwargs) if callable(self.answer) else self.answer
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=answer)])


def _setup(company, cid="5.18"):
    control = control_index()[cid]
    hits = Retriever(company).search(control)
    return control, hits, Context(company, AS_OF, "es")


def test_verified_citation_is_kept_and_fake_one_dropped(company):
    control, hits, ctx = _setup(company)
    chunk = next(h.chunk for h in hits if h.chunk.doc_id == "POL-02")
    real_quote = chunk.text.split(".")[0]
    client = FakeClient({
        "verdict": "partial", "rationale": "Solo una revisión en 2026.", "action": "fix",
        "action_text": "Hacer las revisiones trimestrales.", "confidence": "high",
        "citations": [{"chunk_id": chunk.id, "quote": real_quote},
                      {"chunk_id": chunk.id, "quote": "Las revisiones se hacen todos los días"}],
        "contradictions": ["La política promete revisiones trimestrales y hay una sola."],
    })
    a = ClaudeAssessor(client=client, cache_dir=None).assess(control, hits, ctx)
    assert a.verdict == Verdict.PARTIAL and a.action == Action.FIX
    assert [c.chunk_id for c in a.citations] == [chunk.id]
    assert len(a.notes) == 1 and a.root_cause == "contradiction"


def test_positive_verdict_without_valid_citations_needs_review(company):
    control, hits, ctx = _setup(company)
    client = FakeClient({"verdict": "met", "rationale": "Todo bien.", "action": "none", "action_text": "",
                         "confidence": "high", "citations": [{"chunk_id": "NOPE#1", "quote": "inventado"}]})
    a = ClaudeAssessor(client=client, cache_dir=None).assess(control, hits, ctx)
    assert a.verdict == Verdict.UNDETERMINED


def test_request_shape_forces_the_tool_and_caches_system(company):
    control, hits, ctx = _setup(company)
    client = FakeClient({"verdict": "not_met", "rationale": "x", "action": "add", "action_text": "y",
                         "confidence": "low", "citations": []})
    ClaudeAssessor(client=client, cache_dir=None, model="claude-test").assess(control, hits, ctx)
    req = client.requests[0]
    assert req["model"] == "claude-test"
    assert req["tool_choice"] == {"type": "tool", "name": "record_assessment"}
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Spanish" in req["system"][0]["text"]


def test_answers_are_cached_on_disk(company, tmp_path):
    control, hits, ctx = _setup(company)
    client = FakeClient({"verdict": "not_met", "rationale": "x", "action": "add", "action_text": "y",
                         "confidence": "low", "citations": []})
    assessor = ClaudeAssessor(client=client, cache_dir=tmp_path)
    assessor.assess(control, hits, ctx)
    assessor.assess(control, hits, ctx)
    assert assessor.calls == 1 and len(list(tmp_path.glob("*.json"))) == 1


def test_prompt_flags_superseded_and_expired_documents(company):
    control, hits, ctx = _setup(company, "5.17")
    prompt = build_user_prompt(control, hits, ctx)
    assert "SUPERSEDED" in prompt  # the 2019 password policy
    control, hits, ctx = _setup(company, "5.26")
    assert "REVIEW OVERDUE" in build_user_prompt(control, hits, ctx)


def test_engine_runs_end_to_end_with_claude(company):
    def answer(req):
        return {"verdict": "not_met", "rationale": "Sin evidencia.", "action": "add", "action_text": "Crear.",
                "confidence": "medium", "citations": []}
    r = analyze(company, ClaudeAssessor(client=FakeClient(answer), cache_dir=None), as_of=AS_OF,
                only=["5.7", "8.12"])
    assert all(c.final == Verdict.NOT_MET for c in r.controls)
    assert r.assessor == "claude"
