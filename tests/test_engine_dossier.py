"""engine 里 dossier 开关：enable_dossier=False 时不产出 dossier、不改动生成。

用 monkeypatch 把 PersonaExpander/analyst/writer 换成 spy，避免真实 LLM/TTS。
"""
import types
from echuu.core.persona_dossier import CharacterDossier, Conflict


def _make_engine(monkeypatch):
    from echuu.live import engine as engmod
    eng = engmod.EchuuLiveEngine.__new__(engmod.EchuuLiveEngine)
    # 只装配本测试用到的字段
    from echuu.core.persona_expander import PersonaExpander
    eng.persona_expander = PersonaExpander()
    eng.persona_card = None
    eng.dossier = None
    eng.llm_gen = None  # _maybe_expand passes this through to expand(); spy ignores it
    return eng, engmod


def test_enable_dossier_false_skips_expander(monkeypatch):
    eng, engmod = _make_engine(monkeypatch)
    called = {"expand": 0}

    def fake_expand(self, *a, **k):
        called["expand"] += 1
        return CharacterDossier(conflict=Conflict(statement="x"))

    monkeypatch.setattr(engmod.PersonaExpander, "expand", fake_expand, raising=True)
    # 直接测私有 helper：按 enable 决定要不要 expand
    d = eng._maybe_expand("n", "p", "b", enable_dossier=False)
    assert d is None
    assert called["expand"] == 0


def test_enable_dossier_true_runs_expander(monkeypatch):
    eng, engmod = _make_engine(monkeypatch)

    def fake_expand(self, *a, **k):
        return CharacterDossier(conflict=Conflict(statement="她记账"))

    monkeypatch.setattr(engmod.PersonaExpander, "expand", fake_expand, raising=True)
    d = eng._maybe_expand("n", "p", "b", enable_dossier=True)
    assert d is not None and d.conflict.statement == "她记账"
