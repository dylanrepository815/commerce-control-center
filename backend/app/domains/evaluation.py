from app.domains.schemas import CandidateInput

RULE_VERSION = "v1"
FORBIDDEN = {
    "gambling",
    "casino",
    "adult",
    "pornography",
    "drugs",
    "phishing",
    "scams",
    "malware",
    "severe spam",
}
ALIASES = {
    "scam": "scams",
    "gambling casino": "gambling",
    "adult pornography": "adult",
    "severe spamming": "severe spam",
}


def category(value):
    value = " ".join(
        value.lower().replace("/", " ").replace("_", " ").replace("-", " ").split()
    )
    return ALIASES.get(value, value)


def evaluate(c: CandidateInput):
    reasons = []
    warnings = list(c.warnings)
    categories = sorted({category(cat) for e in c.evidence for cat in e.categories})
    forbidden = sorted(
        {
            category(cat)
            for e in c.evidence
            if e.verified and e.check_type == "history"
            for cat in e.categories
        }
        & FORBIDDEN
    )
    if forbidden:
        reasons.append(
            "Verified forbidden historical categories: " + ", ".join(forbidden)
        )
    if c.scamadviser_score is not None and c.scamadviser_score < 75:
        reasons.append("ScamAdviser score is below the required 75")
    checks = {
        "history": c.history_status,
        "backlinks": c.backlink_status,
        "safety": c.safety_status,
    }
    for key, status in checks.items():
        if status != "CLEAR":
            warnings.append(f"{key.title()} check is {status.lower()}")
    verified = {e.check_type for e in c.evidence if e.verified}
    required = {"history", "backlinks", "safety", "scamadviser", "niche_fit"}
    missing = required - verified
    if missing:
        warnings.append("Missing verified evidence: " + ", ".join(sorted(missing)))
    if c.scamadviser_score is None:
        warnings.append("ScamAdviser score is unavailable")
    if c.niche_fit_score is None:
        warnings.append("Niche fit score is unavailable")
    if any(not e.verified for e in c.evidence):
        warnings.append("Unverified evidence requires review")
    # V1: history 25, backlinks 15, safety 25, ScamAdviser 20, niche fit 15.
    score = round(
        25 * (c.history_status == "CLEAR")
        + 15 * (c.backlink_status == "CLEAR")
        + 25 * (c.safety_status == "CLEAR")
        + 0.20 * (c.scamadviser_score or 0)
        + 0.15 * (c.niche_fit_score or 0)
    )
    status = "FAIL" if reasons else "REVIEW" if warnings else "PASS"
    return dict(
        final_status=status,
        domain_score=score,
        historical_categories=categories,
        warnings=warnings,
        rejection_reasons=reasons,
    )
