import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from devis_extractor import api
from devis_extractor.llm_extraction import ExtractionImpossible
from devis_extractor.schemas import Devis

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
MANIFEST = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
client = TestClient(api.app)


def fake_llm_for(name: str):
    """Faux LLM : renvoie la vérité terrain du document, ou refuse s'il n'y en a pas."""
    expected = SAMPLES / "expected" / f"{Path(name).stem}.json"

    def fake(text: str) -> Devis:
        assert len(text) > 0  # le LLM doit bien recevoir le texte extrait
        if not expected.exists():
            raise ExtractionImpossible("pas un devis")
        return Devis.model_validate_json(expected.read_text(encoding="utf-8"))

    return fake


@pytest.mark.parametrize("doc", MANIFEST, ids=lambda d: d["fichier"])
def test_extract(doc, monkeypatch):
    monkeypatch.setattr(api, "extract_devis", fake_llm_for(doc["fichier"]))
    path = SAMPLES / doc["fichier"]

    response = client.post("/extract", files={"file": (path.name, path.read_bytes())})

    assert response.status_code == int(doc["attendu"])
    if response.status_code == 200:
        expected = json.loads((SAMPLES / "expected" / f"{path.stem}.json").read_text())
        assert response.json() == expected
    else:
        assert "detail" in response.json()


def test_scan_ne_sollicite_pas_le_llm(monkeypatch):
    def interdit(text):
        raise AssertionError("le LLM ne doit pas être appelé pour un scan")

    monkeypatch.setattr(api, "extract_devis", interdit)
    path = SAMPLES / "20_scan_illisible.pdf"
    response = client.post("/extract", files={"file": (path.name, path.read_bytes())})
    assert response.status_code == 422


def test_format_non_supporte():
    response = client.post("/extract", files={"file": ("photo.jpg", b"\xff\xd8\xff")})
    assert response.status_code == 422


def test_fichier_manquant():
    response = client.post("/extract")
    assert response.status_code == 422  # validation automatique FastAPI