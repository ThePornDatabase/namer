FROM ubuntu:impish as APP

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
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

COPY . /opt/renamer/
RUN pip3 install pylint -r /opt/renamer/requirements.txt

FROM APP as TEST
RUN /usr/bin/python3 -m unittest discover -s /opt/renamer -p '*.py'
RUN pylint --rcfile=/opt/renamer/.pylintrc /opt/renamer/*.py
FROM APP
RUN rm -r /opt/renamer/test/

ARG BUILD_DATE
ARG GIT_HASH

ENV PYTHONUNBUFFERED=1
ENV NAMER_CONFIG=/config/namer.cfg
ENV BUILD_DATE=$BUILD_DATE
ENV GIT_HASH=$GIT_HASH
CMD ["/opt/renamer/namer_watchdog.py"]
ENTRYPOINT ["python3"]

