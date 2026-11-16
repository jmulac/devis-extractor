import os

from openai import OpenAI
from pydantic import BaseModel, Field

from devis_extractor.schemas import Devis

SYSTEM_PROMPT = """Tu extrais les données d'un devis commercial français.
Règles :
- Si le document n'est pas un devis (ou proposition commerciale), mets est_un_devis=false,
  explique pourquoi dans raison, et devis=null.
- N'invente rien : un champ absent du document vaut null.
- Montants en nombre décimal avec un point (1 234,56 € -> 1234.56), sans symbole.
- Dates au format AAAA-MM-JJ. Si seule une durée de validité est donnée
  (« valable 30 jours »), calcule date_validite à partir de date_devis.
- reference_emetteur = le code article tel qu'écrit par l'émetteur.
- ean uniquement si un code-barres EAN/Gencod à 8 ou 13 chiffres est présent."""


class ResultatExtraction(BaseModel):
    est_un_devis: bool
    raison: str | None = Field(description="Pourquoi ce n'est pas un devis, sinon null")
    devis: Devis | None


class ExtractionImpossible(Exception):
    pass


def extract_devis(text: str, client: OpenAI | None = None) -> Devis:
    client = client or OpenAI()  # lit OPENAI_API_KEY dans l'environnement
    completion = client.chat.completions.parse(
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format=ResultatExtraction,
    )
    result = completion.choices[0].message.parsed
    if result is None or not result.est_un_devis or result.devis is None:
        raison = result.raison if result else "réponse du modèle refusée ou vide"
        raise ExtractionImpossible(raison or "document non reconnu comme devis")
    return result.devis