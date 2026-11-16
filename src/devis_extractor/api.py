from fastapi import FastAPI, HTTPException, UploadFile

from devis_extractor.llm_extraction import ExtractionImpossible, extract_devis
from devis_extractor.schemas import Devis
from devis_extractor.text_extraction import DocumentInexploitable, extract_text

app = FastAPI(title="Devis extractor")


@app.post("/extract", response_model=Devis)
async def extract(file: UploadFile) -> Devis:
    content = await file.read()
    try:
        text = extract_text(file.filename or "", content)
        return extract_devis(text)
    except (DocumentInexploitable, ExtractionImpossible) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e