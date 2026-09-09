import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import utils
from . import auto_monitor
from .routes import risk, forecast, alerts, explainability


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background periodic monitoring task (every 60 seconds)
    async def periodic_monitor():
        while True:
            await asyncio.sleep(60)
            try:
                auto_monitor.check_and_dispatch_automatic_alerts()
            except Exception:
                pass

    task = asyncio.create_task(periodic_monitor())
    yield
    task.cancel()


app = FastAPI(title='SIH26001 Landslide Risk API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk.router)
app.include_router(forecast.router)
app.include_router(alerts.router)
app.include_router(explainability.router)


@app.get('/health')
def health():
    """Return system health and dataset load status."""
    dataset_status = utils.check_datasets()
    overall_ok = all(v.get('present', False) and v.get('rows', 0) > 0 for v in dataset_status.values())
    return {
        'status': 'ok' if overall_ok else 'degraded',
        'datasets': dataset_status
    }
