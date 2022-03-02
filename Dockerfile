FROM ubuntu:impish as BASE

ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       ffmpeg \
       libffi-dev \
       libssl-dev \
       python3 \
       systemd \
       systemd-sysv \
       wget \
       python3-pip \
       python3-dev \
       python3.9-venv \
       curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

FROM BASE as BUILD
RUN mkdir /work/
COPY . /work/
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && export PATH="/root/.local/bin:$PATH" \
    && cd /work/ \
    && rm -rf /work/namer/__pycache__/ || true \
    && rm -rf /work/test/__pycache__/ || true \
    && poetry install \
    && poetry run pytest \
    && poetry run pylint namer \
    && poetry build
FROM BASE
COPY --from=BUILD /work/dist/namer-0.1.0.tar.gz /
RUN pip3 install /namer-0.1.0.tar.gz \
    && rm /namer-0.1.0.tar.gz

ARG BUILD_DATE
ARG GIT_HASH

ENV PYTHONUNBUFFERED=1
ENV NAMER_CONFIG=/config/namer.cfg
ENV BUILD_DATE=$BUILD_DATE
ENV GIT_HASH=$GIT_HASH
ENTRYPOINT ["python3", "-m", "namer", "watchdog"]

