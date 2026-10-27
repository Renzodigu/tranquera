"""Loads the bundled control catalogs (ISO/IEC 27001:2022 Annex A, NIST CSF 2.0 and Ley 25.326)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

import yaml

from .models import Control, Severity

THEMES = ("organizational", "people", "physical", "technological", "privacy")
ISO = "iso27001-2022"
NIST = "nist-csf-2.0"
LEY_25326 = "ley-25326"
FRAMEWORKS = (ISO, NIST, LEY_25326)
DEFAULT_FRAMEWORKS = (ISO, NIST)


@dataclass(frozen=True)
class NistCatalog:
    functions: dict[str, dict[str, str]]
    categories: dict[str, dict[str, str]]
    subcategories: dict[str, dict[str, str]]

    def function_of(self, sub_id: str) -> str:
        return sub_id.split(".")[0]

    def category_of(self, sub_id: str) -> str:
        return sub_id.split("-")[0]


def _load_yaml(name: str) -> dict:
    text = resources.files("tranquera").joinpath("catalogs", name).read_text(encoding="utf-8")
    return yaml.safe_load(text)


@lru_cache(maxsize=1)
def iso_controls() -> tuple[Control, ...]:
    data = _load_yaml("iso27001_2022.yaml")
    return tuple(
        Control(
            id=str(c["id"]),
            theme=c["theme"],
            criticality=Severity(c["crit"]),
            title_en=c["en"],
            title_es=c["es"],
            keywords=tuple(c.get("kw", [])),
            nist=tuple(c.get("nist", [])),
        )
        for c in data["controls"]
    )


@lru_cache(maxsize=1)
def ley_controls() -> tuple[Control, ...]:
    data = _load_yaml("ley25326.yaml")
    return tuple(
        Control(
            id=str(c["id"]),
            theme="privacy",
            criticality=Severity(c["crit"]),
            title_en=c["en"],
            title_es=c["es"],
            keywords=tuple(c.get("kw", [])),
            nist=tuple(c.get("nist", [])),
            framework=LEY_25326,
            refs=tuple(c.get("refs", [])),
            iso=tuple(str(i) for i in c.get("iso", [])),
        )
        for c in data["obligations"]
    )


@lru_cache(maxsize=1)
def nist_catalog() -> NistCatalog:
    data = _load_yaml("nist_csf_2.yaml")
    return NistCatalog(data["functions"], data["categories"], data["subcategories"])


def controls_for(frameworks: Iterable[str]) -> tuple[Control, ...]:
    """Assessable controls for the frameworks in scope. Annex A is always assessed."""
    return iso_controls() + (ley_controls() if LEY_25326 in set(frameworks) else ())


def control_index() -> dict[str, Control]:
    return {c.id: c for c in iso_controls() + ley_controls()}
