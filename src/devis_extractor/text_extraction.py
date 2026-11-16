from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIN_CHARS = 50  # en dessous, on considère le document inexploitable


class DocumentInexploitable(Exception):
    """Levée quand on ne peut pas obtenir de texte utile (scan, PDF corrompu, format inconnu)."""


def extract_text(filename: str, content: bytes) -> str:
    name = filename.lower()

    if name.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as e:
            raise DocumentInexploitable(f"PDF illisible : {e}") from e
    elif name.endswith(".txt"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        raise DocumentInexploitable(f"Format non supporté : {filename}")

    text = text.strip()
    if len(text) < MIN_CHARS:
        raise DocumentInexploitable("Aucun texte exploitable (document scanné ?)")
    return text