FROM ubuntu:impish as BASE

ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3-pip \
       python3 \
       ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

FROM BASE AS BUILD
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libffi-dev \
       libssl-dev \
       systemd \
       systemd-sysv \
       python3-pip \
       python3-dev \
       python3.9-venv \
       curl \
       nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN mkdir /work/
COPY . /work
RUN cd /work/ \
    && export PATH="/root/.local/bin:$PATH" \
    && rm -rf /work/namer/__pycache__/ || true \
    && rm -rf /work/test/__pycache__/ || true \
    && poetry install \
    && poetry run pytest \
    && poetry run flakeheaven lint \
    && yarn install \
    && yarn run build \
    && poetry build

FROM BASE
COPY --from=BUILD /work/dist/namer-*.tar.gz /
RUN pip3 install /namer-*.tar.gz \
    && rm /namer-*.tar.gz

ARG BUILD_DATE
ARG GIT_HASH
ARG PROJECT_VERSION

ENV PYTHONUNBUFFERED=1
ENV NAMER_CONFIG=/config/namer.cfg
ENV BUILD_DATE=$BUILD_DATE
ENV GIT_HASH=$GIT_HASH
ENV PROJECT_VERSION=$PROJECT_VERSION
EXPOSE 6980
ENTRYPOINT ["python3", "-m", "namer", "watchdog"]

