from typing import Protocol

from reportr.storage import ReportSession


class ActivityReportPdfRenderer(Protocol):
    def render(self, session: ReportSession) -> bytes:
        """Render a report session into PDF bytes."""
        ...


class RendererNotReadyError(RuntimeError):
    pass


class UnconfiguredActivityReportPdfRenderer:
    def render(self, session: ReportSession) -> bytes:
        raise RendererNotReadyError(
            "Activity report renderer is not configured yet. "
            "Implement activity_report_pdf_renderer before calling generate."
        )
