# Backend (FastAPI)

Create and activate a Python virtual environment, then install dependencies:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
pip install -r requirements.txt
```

Run the API server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify health endpoint:

```bash
curl http://localhost:8000/health
```
