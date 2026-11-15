---
lab5_triage:
  image: ghcr.io/szymonw821/itsm-svcdesk@sha256:8de97bff86c49fee9b433b459b4d059d8ca213f45adb562902359be3304b5ee4
  sarif_receipt: 437
---
<!-- ai-generated: 90% - Claude Code (Opus 5.5) drafted the rows and the Bake-off from the receipted SARIF and bakeoff.json; reviewed by the author -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which.

The receipted SARIF (issue 437) has two rules with results outside `lab5-canary/`, both Semgrep, both on the Lab 3
kind manifest. Trivy, Grype and OSV-Scanner report nothing on my own code: the image gate was made green before the
canary by pinning `python:3.13-slim` by digest, running `apt-get upgrade` at build time, removing pip after install
and moving to FastAPI 0.163.1 / Starlette 1.10.0 / Pydantic 2.14.3 (commit 5b47ac4). `.trivyignore` has no entries.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| semgrep | yaml.kubernetes.security.run-as-non-root.run-as-non-root | accept | k8s/svcdesk.yaml:15 (kb-index) and :43 (svcdesk) set no runAsNonRoot. The manifest only runs on a local kind cluster for the Lab 3 Stretch 3 ServiceMonitor and is never deployed; the svcdesk image itself already runs as USER svcdesk (Dockerfile). Accepted until 2027-02-15, when a securityContext with runAsNonRoot: true is added if the manifest is reused. |
| semgrep | yaml.kubernetes.security.allow-privilege-escalation-no-securitycontext.allow-privilege-escalation-no-securitycontext | accept | k8s/svcdesk.yaml:17 and :45 have no securityContext with allowPrivilegeEscalation: false. Same scope as above: a throwaway local kind cluster, no secrets, no exposure outside the laptop; kb-index is the course's seeded-toxic image. Accepted until 2027-02-15. |
| gitleaks | generic-api-key | ignore | k8s/evidence.json:5545 is Helm's pod annotation checksum/secret in the Lab 3 kube-prometheus-stack dump: a SHA-256 digest of a rendered Secret, not a credential. Ignored by fingerprint in .gitleaksignore with that reason. |

## Bake-off

My canary set has 10 labelled defects: 5 in code (3 injection, 1 insecure transport, 1 unsafe deserialization),
3 hard-coded secrets and 2 vulnerable dependency pins (Jinja2, PyYAML). From `bakeoff.json`:

| tool | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|
| semgrep | 6 | 1 | 4 | 0.857 | 0.600 | 0.706 |
| trivy | 2 | 0 | 8 | 1.000 | 0.200 | 0.333 |
| grype | 2 | 0 | 8 | 1.000 | 0.200 | 0.333 |
| osv-scanner | 2 | 0 | 8 | 1.000 | 0.200 | 0.333 |
| gitleaks | 1 | 0 | 9 | 1.000 | 0.100 | 0.182 |

Read per tool, the low recalls of the dependency scanners are not a weakness: Trivy, Grype and OSV-Scanner each found
both vulnerable pins (D03, D05) and nothing else, which is everything they are built to see - recall over the whole set
punishes them for classes outside their scope. The three are redundant with each other on this set; I would gate on one
(Trivy, which also scans the image) and keep a second as a cross-check of the advisory database, not as a second gate.

Semgrep is the only detector that sees code: all five code defects (A02, A04, A09, A11, A14) and one secret (C06). Its
one false positive is `python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1` on
`lab5-canary/app/etag.py:7`, SHA-1 used as an ETag content fingerprint - right about the API, wrong about the risk.
Precision 0.857 means a 14% false positive rate, above Tricorder's 10% bar, and all of it comes from the weak-crypto
class. So I would gate on its injection, deserialization and transport rules (here 5 of 5, no false positives) and
leave weak-crypto as a report a human reads.

Gitleaks is the surprise: precision 1.0 but only C06 of three secrets. C04 (`PORTAL_JWT_SECRET`, a readable passphrase)
and C05 (`SMTP_PASSWORD`, a 16-character random string) were missed by every detector: both are plain string literals
assigned to a well-named variable, with no provider prefix and, for C04, low entropy - the shape that regex-and-entropy
scanners skip. A custom gitleaks rule on variable names (`*_SECRET`, `*_PASSWORD` assigned a literal) would close that
gap at some cost in precision.

My gate: Trivy (deps and image) + gitleaks + Semgrep's high-confidence rules. Together they found 8 of 10 defects with
one false positive. Every recall here is an upper bound: the set is seeded, small (10 defects) and written to be found,
real defects are subtler, and nobody counts the ones that were never labelled.
