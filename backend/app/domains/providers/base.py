from typing import Protocol
from app.domains.schemas import CandidateInput


class DomainProvider(Protocol):
    """Implement with licensed APIs or explicitly authorized data sources only.

    Providers supply evidence, never approval decisions or purchase actions.
    Calls must have bounded timeouts. Validate all output before persistence.
    """

    key: str
    is_demo: bool

    def research(
        self, project_id: str, market: str, niche: str
    ) -> list[CandidateInput]: ...
