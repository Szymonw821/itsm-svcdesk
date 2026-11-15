# Two rules from API.md section 9: install every dependency at BUILD time (the grader's sandbox has no
# network once the image is built) and listen on port 8080 inside the container.
# Lab 5: base image pinned by digest (python:3.13-slim, pulled 2026-11-15) and Debian packages upgraded at build
# time, so the image gate (Trivy, HIGH/CRITICAL with a fix) starts from current fixes.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so Docker caches this layer while editing code. pip is removed afterwards: it is needed only to
# install, and its vendored packages (pip/_vendor) carry fixable CVEs the image gate would report.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip uninstall -y pip

# Code lives under src/svcdesk (see src/README.md).
COPY src/ /app/src/
# Lab 2: the DORA metric computation lives under metrics/ at the repository root.
COPY metrics/ /app/metrics/
ENV PYTHONPATH=/app

EXPOSE 8080
CMD ["uvicorn", "svcdesk.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
