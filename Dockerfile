FROM ubuntu:jammy as base

ENV TZ=Europe/London
ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3-pip \
       python3 \
       ffmpeg \
       tzdata \
       curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

FROM base AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libffi-dev \
       libssl-dev \
       systemd \
       systemd-sysv \
       python3-pip \
       python3-dev \
       python3-venv \
       curl \
       wget \
       gnupg2 \
       xvfb \
       golang \
       git \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

ENV DISPLAY=:99
ARG CHROME_VERSION="google-chrome-stable"
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update -qqy \
  && apt-get -qqy install \
    ${CHROME_VERSION:-google-chrome-stable} \
  && rm /etc/apt/sources.list.d/google-chrome.list \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
RUN apt-get install -y --no-install-recommends \
        nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean
RUN npm install --global pnpm

RUN mkdir /work/
COPY . /work
ENV PATH="/root/.local/bin:$PATH"
WORKDIR /work
RUN rm -rf /work/namer/__pycache__/ || true \
    && rm -rf /work/test/__pycache__/ || true \
    && poetry install
RUN ( Xvfb :99 & cd /work/ && poetry run poe build_all )

FROM base
COPY --from=build /work/dist/namer-*.tar.gz /
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
HEALTHCHECK --interval=1m --timeout=30s CMD curl -s $(python3 -m namer url)/api/healthcheck >/dev/null || exit 1
ENTRYPOINT ["python3", "-m", "namer", "watchdog"]
