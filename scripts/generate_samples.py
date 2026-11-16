"""Génère un corpus de devis fictifs (PDF + TXT) et la vérité terrain JSON associée.

Usage : uv run python scripts/generate_samples.py

Toutes les entreprises, personnes, SIRET et EAN sont fictifs.
"""

import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from devis_extractor.schemas import Devis

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
EXPECTED = OUT / "expected"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT = FONT_DIR / "DejaVuSans.ttf"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

rng = random.Random(42)
CENT = Decimal("0.01")
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


# --- Données fictives -------------------------------------------------------

def ean13(base12: str) -> str:
    """Ajoute la clé de contrôle EAN-13."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


@dataclass
class Partie:
    nom: str
    siret: str | None = None
    tva: str | None = None
    adresse: str = ""


BOUTIQUE = Partie("Maison Clémence", "81234567800017", "FR45812345678",
                  "12 rue des Tanneurs, 35000 Rennes")
CONCURRENTS = [
    Partie("Déco & Sens SARL", "79876543200025", "FR12798765432",
           "4 avenue Foch, 44000 Nantes"),
    Partie("L'Atelier du Logis", "85511122200031", "FR78855111222",
           "ZA du Moulin, 56000 Vannes"),
]
PRESTATAIRES = [
    Partie("Pose Express 35", "90011122300014", "FR33900111223",
           "8 impasse des Lilas, 35510 Cesson-Sévigné"),
    Partie("TransMeubles Ouest", "88822233300019", "FR61888222333",
           "Parc d'activités Est, 35700 Rennes"),
    Partie("Studio Lumen", "91233344400022", None,
           "3 quai Duguay-Trouin, 35000 Rennes"),
]
CLIENTS = [
    Partie("Camille Durand", adresse="5 rue Fictive, 35200 Rennes"),
    Partie("Hôtel Les Embruns", "70012345600011", "FR90700123456",
           "Digue de la Mer, 35800 Dinard"),
    Partie("Restaurant Le Comptoir", "75544433300028", None,
           "21 place des Lices, 35000 Rennes"),
    Partie("Lucas Martin", adresse="17 allée Imaginaire, 35136 Saint-Jacques"),
    Partie("SCI Les Tilleuls", "83322211100015", None,
           "2 chemin Inventé, 35590 L'Hermitage"),
    Partie("Agence Pixel & Co", "82266677700013", "FR22822666777",
           "9 boulevard de la Liberté, 35000 Rennes"),
]

PREFIXES = {"Déco & Sens SARL": "DS", "L'Atelier du Logis": "ADL"}
EMAILS = {"Maison Clémence": "maisonclemence", "L'Atelier du Logis": "atelierdulogis"}

# Catalogue de la boutique : (ref, ean, désignation, prix HT)
CATALOGUE = [
    ("MC-CH-001", ean13("370012300001"), "Chaise bistrot chêne naturel", "45.00"),
    ("MC-CH-002", ean13("370012300002"), "Chaise scandinave velours vert", "79.00"),
    ("MC-TB-010", ean13("370012300010"), "Table ronde 120 cm pied central", "389.00"),
    ("MC-TB-011", ean13("370012300011"), "Table basse rotin 80 x 50 cm", "149.00"),
    ("MC-LU-020", ean13("370012300020"), "Suspension lin naturel 45 cm", "69.90"),
    ("MC-LU-021", ean13("370012300021"), "Lampe à poser céramique blanche", "54.00"),
    ("MC-TX-030", ean13("370012300030"), "Coussin lin lavé 45 x 45 terracotta", "24.90"),
    ("MC-TX-031", ean13("370012300031"), "Tapis jute tressé 160 x 230 cm", "199.00"),
    ("MC-RG-040", ean13("370012300040"), "Étagère murale métal noir 3 niveaux", "119.00"),
    ("MC-RG-041", ean13("370012300041"), "Buffet bas 2 portes cannage", "549.00"),
    ("MC-DC-050", ean13("370012300050"), "Miroir rond laiton 60 cm", "89.00"),
    ("MC-DC-051", ean13("370012300051"), "Vase grès émaillé bleu nuit", "32.50"),
]

# Mêmes produits vus par les concurrents : autre réf, autre libellé, parfois le même EAN.
CONCURRENT_LIBELLES = {
    "MC-CH-001": "Chaise type bistrot en chêne massif",
    "MC-CH-002": "Chaise velours vert style nordique",
    "MC-TB-010": "Table de repas ronde Ø120",
    "MC-LU-020": "Luminaire suspendu en lin (Ø45)",
    "MC-TX-031": "Tapis en jute 160x230",
    "MC-RG-041": "Buffet cannage 2 portes",
    "MC-DC-050": "Miroir laiton diamètre 60",
}
AUTRES_CONCURRENT = [
    ("Fauteuil bouclette écru", "329.00"),
    ("Banc d'entrée bois flotté", "189.00"),
    ("Plaid laine mérinos gris", "59.00"),
]

SERVICES = {
    "Pose Express 35": [
        ("Montage et pose de mobilier (forfait demi-journée)", "180.00", "10"),
        ("Fixation murale étagères et miroirs (par élément)", "25.00", "10"),
        ("Évacuation des emballages", "35.00", "10"),
    ],
    "TransMeubles Ouest": [
        ("Livraison Rennes métropole – véhicule 12 m³", "95.00", "20"),
        ("Livraison en étage sans ascenseur (par étage)", "15.00", "20"),
        ("Assurance ad valorem", "22.00", "20"),
    ],
    "Studio Lumen": [
        ("Conseil en décoration – visite et diagnostic", "150.00", "20"),
        ("Planche d'ambiance et plan 2D", "320.00", "20"),
        ("Sélection et suivi des achats (heure)", "65.00", "20"),
    ],
}


# --- Construction d'un devis (vérité terrain) --------------------------------

def money(x) -> Decimal:
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def make_line(designation, prix, qte, ref=None, ean=None, remise=None, tva="20"):
    pu = Decimal(prix)
    total = Decimal(qte) * pu
    if remise:
        total = total * (1 - Decimal(remise) / 100)
    return {
        "designation": designation,
        "reference_emetteur": ref,
        "ean": ean,
        "quantite": Decimal(qte),
        "prix_unitaire_ht": money(pu),
        "remise_pct": Decimal(remise) if remise else None,
        "taux_tva": Decimal(tva),
        "total_ligne_ht": money(total),
    }


def make_devis(numero, d, emetteur, destinataire, lignes, validite_jours=30):
    total_ht = sum(l["total_ligne_ht"] for l in lignes)
    total_tva = sum(money(l["total_ligne_ht"] * l["taux_tva"] / 100) for l in lignes)
    data = {
        "numero_devis": numero,
        "date_devis": d,
        "date_validite": d + timedelta(days=validite_jours) if validite_jours else None,
        "emetteur": {"nom": emetteur.nom, "siret": emetteur.siret, "tva_intracom": emetteur.tva},
        "destinataire": {"nom": destinataire.nom, "siret": destinataire.siret,
                         "tva_intracom": destinataire.tva},
        "devise": "EUR",
        "lignes": lignes,
        "total_ht": money(total_ht),
        "total_tva": money(total_tva),
        "total_ttc": money(total_ht + total_tva),
    }
    return Devis.model_validate(data)  # garantit que la vérité terrain respecte le schéma


def rand_date() -> date:
    return date(2026, 9, 1) + timedelta(days=rng.randint(0, 75))


# --- Formatage français -------------------------------------------------------

def fr_num(x: Decimal) -> str:
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return s


def fr_eur(x: Decimal) -> str:
    return fr_num(x) + " €"


def fr_date_long(d: date) -> str:
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def fr_qte(q: Decimal) -> str:
    return str(int(q)) if q == q.to_integral() else fr_num(q)


def fr_pct(x: Decimal) -> str:
    return fr_qte(x)


# --- Rendu PDF ----------------------------------------------------------------

class Pdf(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.add_font("DV", "", FONT)
        self.add_font("DV", "B", FONT_BOLD)
        self.set_auto_page_break(True, margin=20)
        self.add_page()
        self.set_font("DV", size=9)

    def txt(self, text, size=9, bold=False, h=5, align="L", w=0):
        self.set_font("DV", "B" if bold else "", size)
        self.multi_cell(w, h, text, align=align, new_x="LMARGIN", new_y="NEXT")


def bloc_partie(p: Partie) -> str:
    lines = [p.nom, p.adresse]
    if p.siret:
        lines.append(f"SIRET : {p.siret}")
    if p.tva:
        lines.append(f"TVA intracom. : {p.tva}")
    return "\n".join(l for l in lines if l)


def table(pdf: Pdf, headers, widths, rows, aligns):
    pdf.set_font("DV", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("DV", "", 8)
    for row in rows:
        for v, w, a in zip(row, widths, aligns):
            pdf.cell(w, 6, v, border=1, align=a)
        pdf.ln()


def totaux(pdf: Pdf, dv: Devis, labels=("Total HT", "TVA", "Total TTC")):
    pdf.ln(4)
    for label, val in zip(labels, (dv.total_ht, dv.total_tva, dv.total_ttc)):
        pdf.set_x(120)
        pdf.set_font("DV", "B" if label == labels[2] else "", 10)
        pdf.cell(40, 6, label, border=0)
        pdf.cell(30, 6, fr_eur(val), align="R", new_x="LMARGIN", new_y="NEXT")


def render_boutique(dv: Devis, emetteur: Partie, client: Partie, path: Path):
    """Modèle A : tableau complet, dates JJ/MM/AAAA."""
    pdf = Pdf()
    pdf.txt(emetteur.nom.upper(), size=16, bold=True, h=8)
    pdf.txt(bloc_partie(emetteur), size=8, h=4)
    pdf.ln(4)
    pdf.set_xy(120, 40)
    pdf.txt(f"DEVIS N° {dv.numero_devis}", size=12, bold=True, w=80)
    pdf.set_x(120)
    pdf.txt(f"Date : {dv.date_devis:%d/%m/%Y}\nValable jusqu'au : {dv.date_validite:%d/%m/%Y}",
            w=80)
    pdf.set_x(120)
    pdf.txt("Client :\n" + bloc_partie(client), size=8, h=4, w=80)
    pdf.ln(8)
    rows = []
    for l in dv.lignes:
        rows.append([l.reference_emetteur or "", l.ean or "", l.designation, fr_qte(l.quantite),
                     fr_num(l.prix_unitaire_ht),
                     f"{fr_pct(l.remise_pct)} %" if l.remise_pct else "",
                     f"{fr_pct(l.taux_tva)} %", fr_num(l.total_ligne_ht)])
    table(pdf, ["Réf.", "EAN", "Désignation", "Qté", "P.U. HT", "Remise", "TVA", "Total HT"],
          [20, 25, 60, 10, 18, 14, 12, 21], rows, ["L", "L", "L", "R", "R", "R", "R", "R"])
    totaux(pdf, dv)
    pdf.ln(10)
    pdf.txt("Conditions : acompte de 30 % à la commande, solde à la livraison. "
            "Devis à retourner daté et signé avec la mention « Bon pour accord ».", size=7, h=4)
    pdf.output(path)


def render_concurrent(dv: Devis, emetteur: Partie, client: Partie, path: Path, compact: bool):
    """Modèle B : libellés différents, dates en toutes lettres, TVA unique en pied."""
    pdf = Pdf()
    pdf.txt(f"{emetteur.nom}", size=14, bold=True, h=7, align="C")
    pdf.txt(emetteur.adresse, size=8, align="C")
    pdf.ln(6)
    titre = "PROPOSITION COMMERCIALE" if compact else "Devis estimatif"
    pdf.txt(f"{titre} – Réf. {dv.numero_devis}", size=11, bold=True)
    pdf.txt(f"Établi le {fr_date_long(dv.date_devis)} pour : {client.nom}, {client.adresse}")
    pdf.txt(f"Offre valable {(dv.date_validite - dv.date_devis).days} jours.")
    pdf.ln(4)
    rows = [[l.designation, l.reference_emetteur or "-", l.ean or "-", fr_qte(l.quantite),
             fr_eur(l.prix_unitaire_ht), fr_eur(l.total_ligne_ht)] for l in dv.lignes]
    table(pdf, ["Article", "Code", "Gencod", "Quantité", "Prix unit.", "Montant HT"],
          [62, 22, 28, 18, 25, 25], rows, ["L", "L", "L", "R", "R", "R"])
    totaux(pdf, dv, ("Montant HT", "TVA 20 %", "Net à payer TTC"))
    pdf.ln(8)
    ids = f"SIRET {emetteur.siret}" + (f" – TVA {emetteur.tva}" if emetteur.tva else "")
    pdf.txt(ids, size=7, align="C")
    pdf.output(path)


def render_prestataire(dv: Devis, emetteur: Partie, client: Partie, path: Path):
    """Modèle C : prestations de service, pas de référence ni EAN, TVA par ligne."""
    pdf = Pdf()
    pdf.set_font("DV", "B", 13)
    pdf.cell(0, 8, emetteur.nom, new_x="LMARGIN", new_y="NEXT")
    pdf.txt(bloc_partie(emetteur).split("\n", 1)[1], size=8, h=4)
    pdf.ln(6)
    pdf.txt(f"Devis {dv.numero_devis} du {dv.date_devis:%d.%m.%Y}", size=11, bold=True)
    pdf.txt(f"À l'attention de : {client.nom}")
    pdf.ln(4)
    rows = [[l.designation, fr_qte(l.quantite), fr_num(l.prix_unitaire_ht),
             f"{fr_pct(l.taux_tva)}%", fr_num(l.total_ligne_ht)] for l in dv.lignes]
    table(pdf, ["Prestation", "Qté", "PU HT (€)", "TVA", "Total HT (€)"],
          [100, 15, 25, 15, 25], rows, ["L", "R", "R", "R", "R"])
    totaux(pdf, dv)
    if dv.date_validite:
        pdf.txt(f"Validité de l'offre : jusqu'au {dv.date_validite:%d/%m/%Y}.", size=8)
    pdf.output(path)


def render_txt(dv: Devis, emetteur: Partie, client: Partie, path: Path):
    """Devis envoyé dans le corps d'un mail, texte libre."""
    lignes = "\n".join(
        f"  - {fr_qte(l.quantite)} x {l.designation}"
        + (f" (réf. {l.reference_emetteur})" if l.reference_emetteur else "")
        + f" à {fr_eur(l.prix_unitaire_ht)} HT"
        + (f", remise {fr_pct(l.remise_pct)} %" if l.remise_pct else "")
        + f" => {fr_eur(l.total_ligne_ht)}"
        for l in dv.lignes)
    body = f"""De : contact@{EMAILS[emetteur.nom]}.example
À : {client.nom}
Objet : Votre devis {dv.numero_devis}

Bonjour,

Suite à notre échange, voici notre proposition datée du {fr_date_long(dv.date_devis)} :

{lignes}

Total HT : {fr_eur(dv.total_ht)}
TVA (20 %) : {fr_eur(dv.total_tva)}
Total TTC : {fr_eur(dv.total_ttc)}

Ce devis est valable jusqu'au {dv.date_validite:%d/%m/%Y}.

Bien cordialement,
{emetteur.nom}
{emetteur.adresse}
SIRET {emetteur.siret}
"""
    path.write_text(body, encoding="utf-8")


def render_scan(dv: Devis, emetteur: Partie, client: Partie, path: Path):
    """PDF contenant uniquement une image floutée : aucun texte extractible."""
    img = Image.new("L", (1240, 1754), 248)
    draw = ImageDraw.Draw(img)
    f = ImageFont.truetype(str(FONT), 26)
    y = 80
    text = [emetteur.nom, f"DEVIS {dv.numero_devis}", f"Client : {client.nom}", ""]
    text += [f"{fr_qte(l.quantite)} x {l.designation}  {fr_eur(l.total_ligne_ht)}" for l in dv.lignes]
    text += ["", f"Total TTC : {fr_eur(dv.total_ttc)}"]
    for t in text:
        draw.text((90, y), t, fill=40, font=f)
        y += 46
    img = img.rotate(1.2, fillcolor=248).filter(ImageFilter.GaussianBlur(1.6))
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.image(img, x=0, y=0, w=210)
    pdf.output(path)


def render_hors_sujet(path: Path):
    """Document qui n'est pas un devis (CGV)."""
    pdf = Pdf()
    pdf.txt("Conditions générales de vente – Maison Clémence", size=13, bold=True, h=7)
    pdf.ln(3)
    for i, para in enumerate([
        "Les présentes conditions s'appliquent à toute commande passée sur la boutique.",
        "Les prix sont exprimés en euros toutes taxes comprises. La boutique se réserve le "
        "droit de modifier ses prix à tout moment.",
        "Le client dispose d'un délai de quatorze jours pour exercer son droit de rétractation.",
        "Les produits voyagent aux risques du destinataire, sauf livraison par nos soins.",
    ], start=1):
        pdf.txt(f"Article {i}", bold=True)
        pdf.txt(para)
        pdf.ln(2)
    pdf.output(path)


# --- Génération du corpus -----------------------------------------------------

def pick_catalogue(n):
    return rng.sample(CATALOGUE, n)


def main():
    OUT.mkdir(exist_ok=True)
    EXPECTED.mkdir(exist_ok=True)
    manifest = []

    def save(name, dv, kind, source):
        if dv is not None:
            (EXPECTED / f"{Path(name).stem}.json").write_text(
                dv.model_dump_json(indent=2), encoding="utf-8")
        manifest.append({"fichier": name, "attendu": "200" if dv else "422",
                         "type": kind, "emetteur": source})

    # 1-6 : devis de la boutique (modèle A), avec remises et TVA réduite parfois
    for i in range(1, 7):
        client = CLIENTS[i % len(CLIENTS)]
        lignes = []
        for ref, ean, des, prix in pick_catalogue(rng.randint(2, 6)):
            remise = rng.choice([None, None, "5", "10", "15"])
            lignes.append(make_line(des, prix, rng.randint(1, 12), ref, ean, remise))
        dv = make_devis(f"DEV-2026-{140 + i:04d}", rand_date(), BOUTIQUE, client, lignes)
        name = f"{i:02d}_boutique_devis.pdf"
        render_boutique(dv, BOUTIQUE, client, OUT / name)
        save(name, dv, "pdf", "boutique")

    # 7-11 : concurrents (modèle B), mêmes produits sous d'autres libellés
    idx = 7
    for c_i, conc in enumerate(CONCURRENTS):
        for k in range(3 if c_i == 0 else 2):
            client = rng.choice(CLIENTS)
            lignes = []
            for ref, ean, _, prix in rng.sample(
                    [p for p in CATALOGUE if p[0] in CONCURRENT_LIBELLES], rng.randint(2, 4)):
                prix_c = money(Decimal(prix) * Decimal(rng.choice(["0.92", "0.97", "1.05"])))
                lignes.append(make_line(
                    CONCURRENT_LIBELLES[ref], prix_c, rng.randint(1, 8),
                    ref=f"{PREFIXES[conc.nom]}{rng.randint(10000, 99999)}",
                    ean=ean if rng.random() < 0.6 else None))
            if rng.random() < 0.6:
                des, prix = rng.choice(AUTRES_CONCURRENT)
                lignes.append(make_line(des, prix, rng.randint(1, 3),
                                        ref=f"X{rng.randint(1000, 9999)}"))
            numero = f"{PREFIXES[conc.nom]}-{rng.randint(2000, 9999)}"
            dv = make_devis(numero, rand_date(), conc, client, lignes,
                            validite_jours=rng.choice([15, 30, 60]))
            name = f"{idx:02d}_concurrent_devis.pdf"
            render_concurrent(dv, conc, client, OUT / name, compact=bool(k % 2))
            save(name, dv, "pdf", "concurrent")
            idx += 1

    # 12-16 : prestataires (modèle C)
    for presta in PRESTATAIRES + PRESTATAIRES[:2]:
        client = rng.choice([BOUTIQUE] + CLIENTS)
        lignes = [make_line(des, prix, rng.randint(1, 4), tva=tva)
                  for des, prix, tva in rng.sample(SERVICES[presta.nom], rng.randint(2, 3))]
        dv = make_devis(f"Q{rng.randint(100, 999)}/{2026}", rand_date(), presta, client, lignes,
                        validite_jours=rng.choice([None, 30, 90]))
        name = f"{idx:02d}_prestataire_devis.pdf"
        render_prestataire(dv, presta, client, OUT / name)
        save(name, dv, "pdf", "prestataire")
        idx += 1

    # 17-19 : devis reçus par mail en texte brut
    for emetteur in [BOUTIQUE, CONCURRENTS[1], BOUTIQUE]:
        client = rng.choice(CLIENTS)
        if emetteur is BOUTIQUE:
            lignes = [make_line(des, prix, rng.randint(1, 6), ref, None,
                                rng.choice([None, "10"]))
                      for ref, _, des, prix in pick_catalogue(rng.randint(2, 4))]
        else:
            lignes = [make_line(des, prix, rng.randint(1, 4)) for des, prix in AUTRES_CONCURRENT]
        dv = make_devis(f"D{rng.randint(10000, 99999)}", rand_date(), emetteur, client, lignes)
        name = f"{idx:02d}_mail_devis.txt"
        render_txt(dv, emetteur, client, OUT / name)
        save(name, dv, "txt", "boutique" if emetteur is BOUTIQUE else "concurrent")
        idx += 1

    # 20 : scan sans couche texte -> inexploitable (422 attendu)
    client = CLIENTS[0]
    lignes = [make_line(des, prix, 2, ref, ean) for ref, ean, des, prix in pick_catalogue(3)]
    dv = make_devis("DEV-2026-0199", rand_date(), BOUTIQUE, client, lignes)
    name = f"{idx:02d}_scan_illisible.pdf"
    render_scan(dv, BOUTIQUE, client, OUT / name)
    save(name, None, "pdf-image", "boutique")
    idx += 1

    # 21 : document qui n'est pas un devis (422 attendu)
    name = f"{idx:02d}_cgv_pas_un_devis.pdf"
    render_hors_sujet(OUT / name)
    save(name, None, "pdf", "boutique")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    print(f"{len(manifest)} documents générés dans {OUT}")


if __name__ == "__main__":
    main()
