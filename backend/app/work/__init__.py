"""Work-context and live event tracking for NOVA."""

from app.work.context.service import CurrentWorkStateService

current_work_state_service = CurrentWorkStateService()

__all__ = ["CurrentWorkStateService", "current_work_state_service"]
