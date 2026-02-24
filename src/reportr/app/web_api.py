# pyright: reportUnusedFunction=false

import asyncio
from os import SEEK_END
from typing import BinaryIO
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from reportr.reporting import (
    ActivityReportPdfRenderer,
    RendererNotReadyError,
    UnconfiguredActivityReportPdfRenderer,
    WeasyPrintActivityReportPdfRenderer,
)
from reportr.storage import (
    PHOTO_GROUP_LIMITS,
    FileSystemReportRepository,
    ImageMeta,
    PhotoGroupName,
    ReportFormFields,
    ReportRepository,
    ReportSession,
    ReportStatus,
    SessionNotFoundError,
)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
MAX_SESSION_SIZE_BYTES = 300 * 1024 * 1024
MAX_IMAGE_LONGEST_SIDE = 1200
RENDER_CONCURRENCY_LIMIT = 3
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


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
) -> FastAPI:
    app = FastAPI(title="SBS Reportr API", version="0.1.0")
    app.state.report_repository = repository or FileSystemReportRepository()
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
        missing_requirements = _collect_missing_requirements(session)
        if missing_requirements:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "Report session is incomplete.",
                    "missing": missing_requirements,
                },
            )

        async with app.state.render_semaphore:
            repository.set_status(session_id, ReportStatus.GENERATING)

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

        return GenerateReportResponse(
            session_id=session_id,
            download_url=f"/reports/{session_id}/download",
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


def _build_default_renderer(repository: ReportRepository) -> ActivityReportPdfRenderer:
    if isinstance(repository, FileSystemReportRepository):
        return WeasyPrintActivityReportPdfRenderer(sessions_root=repository.sessions_root)

    return UnconfiguredActivityReportPdfRenderer()


app = create_app()
