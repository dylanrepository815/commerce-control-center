from datetime import datetime, timezone
from app.domains.schemas import CandidateInput, EvidenceInput


class FixtureProvider:
    key = "development-fixture"
    is_demo = True

    def research(self, project_id, market, niche):
        result = []
        for i, (name, score, history, categories) in enumerate(
            [
                ("evergreen-studio", 92, "CLEAR", ["retail"]),
                ("niche-collective", 86, "CLEAR", ["retail"]),
                ("market-foundry", None, "UNKNOWN", []),
                ("caution-store", 68, "CLEAR", ["retail"]),
                ("unsafe-archive", 90, "RISK", ["casino"]),
            ]
        ):
            evidence = [
                EvidenceInput(
                    provider=self.key,
                    check_type=check,
                    source_reference=f"fixture://{project_id}/{i}/{check}",
                    observed_at=datetime.now(timezone.utc),
                    findings=f"SYNTHETIC DEMO: {check} evidence. No live service was queried.",
                    verified=(score is not None),
                    categories=categories if check == "history" else [],
                )
                for check in [
                    "history",
                    "backlinks",
                    "safety",
                    "scamadviser",
                    "niche_fit",
                ]
            ]
            result.append(
                CandidateInput(
                    domain=name + ".example",
                    source="SYNTHETIC DEMO FIXTURE",
                    scamadviser_score=score,
                    history_status=history,
                    backlink_status="CLEAR",
                    safety_status="CLEAR",
                    niche_fit_score=90 - i * 5,
                    evidence=evidence,
                )
            )
        return result
