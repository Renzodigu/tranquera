from datetime import date
from pathlib import Path

import pytest

from tranquera.cli import demo_path
from tranquera.ingest import load_company

AS_OF = date(2026, 10, 20)


@pytest.fixture(scope="session")
def demo_dir() -> Path:
    return demo_path()


@pytest.fixture()
def company(demo_dir):
    return load_company(demo_dir)


def write_doc(folder: Path, name: str, front: str, body: str = "# Doc\n\nTexto.") -> Path:
    path = folder / name
    path.write_text(f"---\n{front.strip()}\n---\n{body}\n", encoding="utf-8")
    return path
