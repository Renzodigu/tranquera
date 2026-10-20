"""Loads the bundled control catalogs (ISO/IEC 27001:2022 Annex A and NIST CSF 2.0)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

import yaml

from .models import Control, Severity

THEMES = ("organizational", "people", "physical", "technological")


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
def nist_catalog() -> NistCatalog:
    data = _load_yaml("nist_csf_2.yaml")
    return NistCatalog(data["functions"], data["categories"], data["subcategories"])


def control_index() -> dict[str, Control]:
    return {c.id: c for c in iso_controls()}
