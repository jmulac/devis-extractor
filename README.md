# devis-extractor

Service FastAPI qui transforme un devis non structuré (PDF ou texte de mail) en JSON validé par Pydantic, grâce à un LLM (OpenAI Structured Outputs).

## Le problème

Une boutique e-commerce reçoit et émet des devis de formats très variés : les siens, ceux de concurrents, ceux de prestataires (pose, livraison, conseil). Ressaisir les lignes pour les comparer ou les rapprocher du catalogue est long et source d'erreurs. Ce service extrait en une requête l'en-tête (numéro, dates, émetteur, destinataire, totaux) et chaque ligne (désignation, référence, EAN, quantité, prix, remise, TVA).

## Lancer le service

Prérequis : Docker et une clé API OpenAI.

```bash
git clone https://github.com/jmulac/devis-extractor.git
cd devis-extractor
cp .env.example .env        # puis renseigner OPENAI_API_KEY
docker compose up --build -d
```

## Exemple de requête

```bash
curl -F "file=@samples/08_concurrent_devis.pdf" http://127.0.0.1:8000/extract
```

| Cas | Réponse |
|---|---|
| Devis lisible (PDF texte ou .txt) | `200` + JSON conforme au schéma `Devis` |
| PDF scanné sans texte, format non supporté | `422` sans appel au LLM |
| Document qui n'est pas un devis | `422` avec la raison donnée par le modèle |

Documentation interactive : http://127.0.0.1:8000/docs

## Architecture

```
fichier → text_extraction (pypdf / txt) → llm_extraction (OpenAI + schéma Pydantic) → API FastAPI
```

- `src/devis_extractor/schemas.py` : schéma cible (montants en `Decimal`, EAN validé).
- `src/devis_extractor/text_extraction.py` : texte brut, rejet des documents inexploitables.
- `src/devis_extractor/llm_extraction.py` : appel au LLM en sortie structurée stricte.
- `src/devis_extractor/api.py` : endpoint `POST /extract`.

## Corpus et tests

`samples/` contient 21 devis **fictifs** générés par `scripts/generate_samples.py`, avec leur vérité terrain dans `samples/expected/`.

```bash
uv sync
uv run pytest
```

Les tests simulent le LLM : ils sont gratuits, rapides (< 1 s) et couvrent chaque document du corpus.

## Limites et suite

- Pas d'OCR : les scans sont rejetés.
- Pas encore de mesure de la précision réelle du LLM sur le corpus.
- Prochaine étape : rapprocher les lignes extraites du catalogue (EAN exact, puis similarité sémantique).