FROM python:3.10.21-slim-bookworm

ARG BUILD_ARCH
ARG BUILD_VERSION=0.1.3-dev
ARG PIP_INDEX_URL=https://pypi.org/simple
LABEL io.hass.type="addon" io.hass.arch=${BUILD_ARCH} io.hass.version=${BUILD_VERSION}
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libffi8 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lib-${BUILD_ARCH} /app/lib-${BUILD_ARCH}
COPY src/ /app/
COPY licenses/ /licenses/

ENV LD_LIBRARY_PATH=/app/lib-${BUILD_ARCH}
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=true

ENTRYPOINT ["python3"]
CMD ["/app/main.py"]