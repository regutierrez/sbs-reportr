from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copyfileobj
from typing import BinaryIO
from uuid import UUID, uuid4

from .models import PhotoGroupName, ImageMeta, ReportFormFields, ReportSession, ReportStatus


class SessionNotFoundError(LookupError):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Report session '{session_id}' was not found")
        self.session_id = session_id


class ReportRepository(ABC):
    @abstractmethod
    def create_session(self) -> ReportSession:
        """Create and persist an empty report session."""

    @abstractmethod
    def get_session(self, session_id: UUID) -> ReportSession | None:
        """Return report session metadata if present."""

    @abstractmethod
    def save_form_fields(self, session_id: UUID, form_fields: ReportFormFields) -> ReportSession:
        """Persist text/number form fields for an existing session."""

    @abstractmethod
    def save_image(
        self,
        session_id: UUID,
        *,
        group_name: PhotoGroupName,
        source: BinaryIO,
        original_filename: str,
        size_bytes: int,
        width: int,
        height: int,
    ) -> ImageMeta:
        """Persist an uploaded image and register image metadata on a session."""

    @abstractmethod
    def persist_generated_pdf(self, session_id: UUID, pdf_bytes: bytes) -> Path:
        """Persist generated report output to long-term storage."""

    @abstractmethod
    def set_status(self, session_id: UUID, status: ReportStatus) -> ReportSession:
        """Update report session status."""


class FileSystemReportRepository(ReportRepository):
    def __init__(
        self,
        *,
        sessions_root: Path = Path("data/sessions"),
        reports_root: Path = Path("data/reports"),
    ) -> None:
        self._sessions_root = sessions_root
        self._reports_root = reports_root

        self._sessions_root.mkdir(parents=True, exist_ok=True)
        self._reports_root.mkdir(parents=True, exist_ok=True)

    @property
    def sessions_root(self) -> Path:
        return self._sessions_root

    @property
    def reports_root(self) -> Path:
        return self._reports_root

    def create_session(self) -> ReportSession:
        session = ReportSession(id=uuid4())
        self._session_directory(session.id).mkdir(parents=True, exist_ok=False)
        self._images_directory(session.id).mkdir(parents=True, exist_ok=True)
        self._write_session(session)
        return session

    def get_session(self, session_id: UUID) -> ReportSession | None:
        metadata_path = self._metadata_path(session_id)
        if not metadata_path.exists():
            return None

        return ReportSession.model_validate_json(metadata_path.read_text(encoding="utf-8"))

    def save_form_fields(self, session_id: UUID, form_fields: ReportFormFields) -> ReportSession:
        session = self._require_session(session_id)
        session.form_fields = form_fields
        self._write_session(session)
        return session

    def save_image(
        self,
        session_id: UUID,
        *,
        group_name: PhotoGroupName,
        source: BinaryIO,
        original_filename: str,
        size_bytes: int,
        width: int,
        height: int,
    ) -> ImageMeta:
        session = self._require_session(session_id)

        image_id = uuid4()
        extension = self._resolve_extension(original_filename)
        stored_filename = f"{image_id}{extension}"
        image_directory = self._images_directory(session_id) / group_name.value
        image_directory.mkdir(parents=True, exist_ok=True)
        image_path = image_directory / stored_filename

        with image_path.open("wb") as destination:
            copyfileobj(source, destination)

        image = ImageMeta(
            id=image_id,
            group_name=group_name,
            original_filename=original_filename,
            stored_filename=stored_filename,
            size_bytes=size_bytes,
            width=width,
            height=height,
        )
        session.images.setdefault(group_name.value, []).append(image)
        self._write_session(session)

        return image

    def persist_generated_pdf(self, session_id: UUID, pdf_bytes: bytes) -> Path:
        session = self._require_session(session_id)

        report_directory = self._reports_root / str(session_id)
        report_directory.mkdir(parents=True, exist_ok=True)
        report_path = report_directory / "report.pdf"
        report_path.write_bytes(pdf_bytes)

        session.generated_pdf_path = report_path.as_posix()
        session.status = ReportStatus.COMPLETED
        self._write_session(session)

        return report_path

    def set_status(self, session_id: UUID, status: ReportStatus) -> ReportSession:
        session = self._require_session(session_id)
        session.status = status
        self._write_session(session)
        return session

    def _require_session(self, session_id: UUID) -> ReportSession:
        session = self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)

        return session

    def _write_session(self, session: ReportSession) -> None:
        metadata_path = self._metadata_path(session.id)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = metadata_path.with_suffix(".tmp")
        temporary_path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        temporary_path.replace(metadata_path)

    def _session_directory(self, session_id: UUID) -> Path:
        return self._sessions_root / str(session_id)

    def _images_directory(self, session_id: UUID) -> Path:
        return self._session_directory(session_id) / "images"

    def _metadata_path(self, session_id: UUID) -> Path:
        return self._session_directory(session_id) / "session.json"

    @staticmethod
    def _resolve_extension(original_filename: str) -> str:
        extension = Path(original_filename).suffix.lower()
        if extension:
            return extension

        return ".bin"
