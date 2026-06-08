"""Pack-driven detection engine + overlap resolution.

Builds a Presidio AnalyzerEngine from a CountryPack's nlp_config + recognizers,
runs detection (with optional CSV column rules), and resolves overlapping spans
(highest score first, then longest span). Engines are cached per locale.
"""
from __future__ import annotations

from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .packs.registry import load_pack


@lru_cache(maxsize=8)
def _engine_for(locale: str):
    pack = load_pack(locale)
    nlp = NlpEngineProvider(nlp_configuration=pack.nlp_config()).create_engine()
    lang = pack.nlp_config()["models"][0]["lang_code"]
    analyzer = AnalyzerEngine(nlp_engine=nlp, supported_languages=[lang])
    for r in pack.recognizers():
        analyzer.registry.add_recognizer(r)
    return analyzer, pack, lang


def detect(text: str, locale: str = "ro_RO", is_csv: bool = False) -> list:
    """Return non-overlapping RecognizerResult spans, sorted by position."""
    analyzer, pack, lang = _engine_for(locale)
    results = analyzer.analyze(text=text, entities=pack.entities, language=lang)
    if is_csv:
        from .packs.ro_RO.columns import analyze_csv  # locale-specific for now
        results = analyze_csv(text, pack.csv_columns()) + list(results)
    # resolve overlaps: prefer higher score, then longer span
    results = sorted(results, key=lambda d: (-d.score, -(d.end - d.start)))
    chosen = []
    for d in results:
        if not any(d.start < a.end and d.end > a.start for a in chosen):
            chosen.append(d)
    return sorted(chosen, key=lambda d: d.start)
