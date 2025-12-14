# 🧾 Utility Bill Ingestion – FastAPI MVP (Template-Free)

This bundle uses PDF.co **convert-to-text** + local **regex parsing** (no PDF.co templates).

## Run
```bash
cd utility-bill-mvp/worker
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt

# Ensure .env at project root has your PDFCO_API_KEY
python app.py
```

Swagger UI → http://localhost:8000/docs

Endpoints:
- GET /health
- POST /parse-file
- POST /process
