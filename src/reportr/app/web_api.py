# pyright: reportUnusedFunction=false

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import timedelta
from os import SEEK_END, getenv
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from reportr.reporting.activity_report_pdf_renderer import (
    ActivityReportPdfRenderer,
    RendererNotReadyError,
    UnconfiguredActivityReportPdfRenderer,
    WeasyPrintActivityReportPdfRenderer,
)
from reportr.storage.models import (
    PHOTO_GROUP_LIMITS,
    ImageMeta,
    PhotoGroupName,
    ReportFormFields,
    ReportSession,
    ReportStatus,
)
from reportr.storage.report_repository import (
    FileSystemReportRepository,
    ReportRepository,
    SessionNotFoundError,
)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
MAX_SESSION_SIZE_BYTES = 300 * 1024 * 1024
MAX_IMAGE_LONGEST_SIDE = 1200
RENDER_CONCURRENCY_LIMIT = 3
ABANDONED_SESSION_TTL_SECONDS = 24 * 60 * 60
SESSION_CLEANUP_INTERVAL_SECONDS = 30 * 60
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

DATA_ROOT_ENV = "REPORTR_DATA_ROOT"
SESSIONS_ROOT_ENV = "REPORTR_SESSIONS_ROOT"
REPORTS_ROOT_ENV = "REPORTR_REPORTS_ROOT"


class SessionStatusResponse(BaseModel):
    session_id: UUID
    status: ReportStatus


class ImageUploadResponse(BaseModel):
    image: ImageMeta


class GenerateReportResponse(BaseModel):
    session_id: UUID
    download_url: str


def create_app(
    repository: ReportRepository | None = None,
    renderer: ActivityReportPdfRenderer | None = None,
    render_semaphore: asyncio.Semaphore | None = None,
    session_ttl_seconds: int = ABANDONED_SESSION_TTL_SECONDS,
    cleanup_interval_seconds: int = SESSION_CLEANUP_INTERVAL_SECONDS,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.cleanup_task = None

        if session_ttl_seconds > 0 and cleanup_interval_seconds > 0:
            app.state.cleanup_task = asyncio.create_task(
                _run_session_cleanup_loop(
                    repository=app.state.report_repository,
                    session_ttl_seconds=session_ttl_seconds,
                    cleanup_interval_seconds=cleanup_interval_seconds,
                )
            )

        try:
            yield
        finally:
            cleanup_task: asyncio.Task[None] | None = app.state.cleanup_task
            if cleanup_task is not None:
                cleanup_task.cancel()
                with suppress(asyncio.CancelledError):
                    await cleanup_task

    app = FastAPI(title="SBS Reportr API", version="0.1.0", lifespan=lifespan)
    app.state.report_repository = repository or _build_default_repository()
    app.state.report_renderer = renderer or _build_default_renderer(app.state.report_repository)
    app.state.render_semaphore = render_semaphore or asyncio.Semaphore(RENDER_CONCURRENCY_LIMIT)

    @app.exception_handler(SessionNotFoundError)
    async def handle_session_not_found(_: Request, exc: SessionNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/reports",
        response_model=SessionStatusResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["reports"],
    )
    async def create_report_session() -> SessionStatusResponse:
        created = app.state.report_repository.create_session()
        return SessionStatusResponse(session_id=created.id, status=created.status)

    @app.put("/reports/{session_id}", response_model=ReportSession, tags=["reports"])
    async def update_report_form_fields(
        session_id: UUID,
        form_fields: ReportFormFields,
    ) -> ReportSession:
        return app.state.report_repository.save_form_fields(session_id, form_fields)

    @app.post(
        "/reports/{session_id}/images/{group_name}",
        response_model=ImageUploadResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["reports"],
    )
    async def upload_report_image(
        session_id: UUID,
        group_name: PhotoGroupName,
        image: UploadFile = File(...),
    ) -> ImageUploadResponse:
        try:
            _validate_image_mime_type(image)

            repository: ReportRepository = app.state.report_repository
            session = _require_session(repository, session_id)

            size_bytes = _get_upload_size(image.file)
            if size_bytes > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image exceeds the 15MB file size limit.",
                )

            max_images = PHOTO_GROUP_LIMITS[group_name][1]
            existing_group_count = len(session.images.get(group_name.value, []))
            if existing_group_count >= max_images:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Photo group '{group_name.value}' already reached its max of {max_images}.",
                )

            existing_total_size = sum(
                image_meta.size_bytes
                for image_set in session.images.values()
                for image_meta in image_set
            )
            if existing_total_size + size_bytes > MAX_SESSION_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Session exceeds the 300MB total upload limit.",
                )

            width, height = _get_image_dimensions(image.file)
            if max(width, height) > MAX_IMAGE_LONGEST_SIDE:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Image dimensions exceed the 1200px longest-side limit.",
                )

            saved_image = repository.save_image(
                session_id,
                group_name=group_name,
                source=image.file,
                original_filename=image.filename or "upload.bin",
                size_bytes=size_bytes,
                width=width,
                height=height,
            )

            return ImageUploadResponse(image=saved_image)
        finally:
            await image.close()

    @app.post(
        "/reports/{session_id}/generate", response_model=GenerateReportResponse, tags=["reports"]
    )
    async def generate_report(session_id: UUID) -> GenerateReportResponse:
        repository: ReportRepository = app.state.report_repository
        report_renderer: ActivityReportPdfRenderer = app.state.report_renderer

        session = _require_session(repository, session_id)

        existing_pdf_path = repository.get_generated_pdf_path(session_id)
        if existing_pdf_path is not None:
            if session.status != ReportStatus.COMPLETED:
                repository.set_status(session_id, ReportStatus.COMPLETED)

            return GenerateReportResponse(
                session_id=session_id,
                download_url=f"/reports/{session_id}/download",
            )

        if session.status == ReportStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Report was already generated, but the generated PDF is no longer available."
                ),
            )

        if session.status == ReportStatus.GENERATING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report generation is already in progress.",
            )

        missing_requirements = _collect_missing_requirements(session)
        if missing_requirements:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "Report session is incomplete.",
                    "missing": missing_requirements,
                },
            )

        repository.set_status(session_id, ReportStatus.GENERATING)

        async with app.state.render_semaphore:
            try:
                latest_session = _require_session(repository, session_id)
                pdf_bytes = await run_in_threadpool(report_renderer.render, latest_session)
            except RendererNotReadyError as exc:
                repository.set_status(session_id, ReportStatus.DRAFT)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
                ) from exc
            except Exception:
                repository.set_status(session_id, ReportStatus.DRAFT)
                raise

            if not pdf_bytes:
                repository.set_status(session_id, ReportStatus.DRAFT)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF renderer returned empty output.",
                )

            repository.persist_generated_pdf(session_id, pdf_bytes)
            repository.cleanup_session_images(session_id)

        return GenerateReportResponse(
            session_id=session_id,
            download_url=f"/reports/{session_id}/download",
        )

    @app.get("/reports/{session_id}/download", tags=["reports"])
    async def download_report(session_id: UUID) -> FileResponse:
        repository: ReportRepository = app.state.report_repository
        pdf_path = repository.get_generated_pdf_path(session_id)
        if pdf_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated report is not available for download.",
            )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"activity-report-{session_id}.pdf",
        )

    return app


def _require_session(repository: ReportRepository, session_id: UUID) -> ReportSession:
    session = repository.get_session(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)

    return session


def _validate_image_mime_type(image: UploadFile) -> None:
    if image.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        allowed_types = ", ".join(sorted(ALLOWED_IMAGE_MIME_TYPES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{image.content_type}'. Allowed types: {allowed_types}.",
        )


def _get_upload_size(source: BinaryIO) -> int:
    source.seek(0, SEEK_END)
    size = source.tell()
    source.seek(0)
    return size


def _get_image_dimensions(source: BinaryIO) -> tuple[int, int]:
    source.seek(0)

    try:
        with Image.open(source) as pil_image:
            width, height = pil_image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded file is not a valid image.",
        ) from exc
    finally:
        source.seek(0)

    return width, height


def _collect_missing_requirements(session: ReportSession) -> dict[str, list[str] | bool]:
    missing: dict[str, list[str] | bool] = {}

    if session.form_fields is None:
        missing["form_fields"] = True

    missing_photo_groups: list[str] = []
    for group_name, (minimum, _) in PHOTO_GROUP_LIMITS.items():
        current_count = len(session.images.get(group_name.value, []))
        if current_count < minimum:
            missing_photo_groups.append(group_name.value)

    if missing_photo_groups:
        missing["photo_groups"] = missing_photo_groups

    return missing


def _resolve_default_data_root() -> Path:
    source_root = Path(__file__).resolve().parents[2]
    if source_root.name == "src":
        return source_root.parent / "data"

    return Path.cwd() / "data"


def _resolve_repository_roots() -> tuple[Path, Path]:
    sessions_root_value = getenv(SESSIONS_ROOT_ENV)
    reports_root_value = getenv(REPORTS_ROOT_ENV)
    data_root_value = getenv(DATA_ROOT_ENV)

    sessions_root = Path(sessions_root_value).expanduser() if sessions_root_value else None
    reports_root = Path(reports_root_value).expanduser() if reports_root_value else None

    if sessions_root is not None and reports_root is not None:
        return sessions_root, reports_root

    data_root = (
        Path(data_root_value).expanduser() if data_root_value else _resolve_default_data_root()
    )

    return (
        sessions_root if sessions_root is not None else data_root / "sessions",
        reports_root if reports_root is not None else data_root / "reports",
    )


def _build_default_repository() -> FileSystemReportRepository:
    sessions_root, reports_root = _resolve_repository_roots()
    return FileSystemReportRepository(sessions_root=sessions_root, reports_root=reports_root)


def _build_default_renderer(repository: ReportRepository) -> ActivityReportPdfRenderer:
    if isinstance(repository, FileSystemReportRepository):
        return WeasyPrintActivityReportPdfRenderer(sessions_root=repository.sessions_root)

    return UnconfiguredActivityReportPdfRenderer()


async def _run_session_cleanup_loop(
    *,
    repository: ReportRepository,
    session_ttl_seconds: int,
    cleanup_interval_seconds: int,
) -> None:
    max_age = timedelta(seconds=session_ttl_seconds)

    while True:
        repository.cleanup_expired_sessions(max_age=max_age)
        await asyncio.sleep(cleanup_interval_seconds)


app = create_app()
