from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Partie(BaseModel):
    """Émetteur ou destinataire du devis."""
    nom: str
    siret: str | None = None
    tva_intracom: str | None = None


class LigneDevis(BaseModel):
    designation: str
    reference_emetteur: str | None = None
    ean: str | None = Field(default=None, pattern=r"^\d{8}$|^\d{13}$")
    quantite: Decimal = Field(gt=0)
    prix_unitaire_ht: Decimal = Field(ge=0)
    remise_pct: Decimal | None = Field(default=None, ge=0, le=100)
    taux_tva: Decimal | None = Field(default=None, ge=0, le=100)
    total_ligne_ht: Decimal


class Devis(BaseModel):
    numero_devis: str
    date_devis: date
    date_validite: date | None = None
    emetteur: Partie
    destinataire: Partie | None = None
    devise: str = Field(default="EUR", min_length=3, max_length=3)
    lignes: list[LigneDevis] = Field(min_length=1)
    total_ht: Decimal
    total_tva: Decimal | None = None
    total_ttc: Decimal | None = None