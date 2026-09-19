# ai-generated: 85% - Claude Code drafted the whole package from docs/REQUIREMENTS.md and docs/API.md, reviewed by the author
"""Priority = impact x urgency matrix, adjusted by decision C3 (VIP reporters), see docs/API.md section 3."""

MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}

# C3 = vip (DECISIONS.md): a VIP reporter's ticket is never lower than P2.
VIP_ESCALATED_FROM = {"P3", "P4"}


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    base = MATRIX[(impact, urgency)]
    if vip and base in VIP_ESCALATED_FROM:
        return "P2"
    return base
