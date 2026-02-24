from fastapi import FastAPI

from reportr.storage import FileSystemReportRepository, ReportRepository


def create_app(repository: ReportRepository | None = None) -> FastAPI:
    app = FastAPI(title="SBS Reportr API", version="0.1.0")
    app.state.report_repository = repository or FileSystemReportRepository()

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
