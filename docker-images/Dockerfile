FROM ghcr.io/astral-sh/uv:python3.11-trixie-slim AS yio-minions-base

# ----------------------------------------------------------------------
# Setup a non root user for execution
RUN useradd --create-home --shell /bin/bash minion
WORKDIR /home/minion
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Install libmagic1 (required for file mimetype detection)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libdmtx0b  \
    qpdf \
    && rm -rf /var/lib/apt/lists/*
# ----------------------------------------------------------------------

FROM yio-minions-base AS build-python

WORKDIR /home/minion
ENV UV_PROJECT_ENVIRONMENT="/home/minion/venv"

# RUN python -m venv /home/minion/venv

# ----------------------------------------------------------------------
# Make sure to set proper settings for python and pip installation
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Install yio-minions locally (from source) and all requirements
COPY . /build
RUN --mount=type=secret,id=uv_credentials,target=/root/.local/share/uv/credentials/credentials.toml \
    # --mount=type=bind,source=.,target=/build \
     cd /build && uv sync --no-dev --no-editable && cd /home/minion

ENV PATH="/home/minion/venv/bin:$PATH"
# ----------------------------------------------------------------------


FROM yio-minions-base AS yio-minions


# ----------------------------------------------------------------------
# All following steps are performed as non-root user
USER minion

# Copy required files for regular version (dependent startup script)
COPY --chown=minion:minion docker-images/general/start.py /home/minion/start.py
COPY --chown=minion:minion docker-images/general/start.sh /home/minion/start.sh
COPY --chown=minion:minion docker-images/general/app /home/minion/app
COPY --chown=minion:minion --from=build-python /home/minion/venv /home/minion/venv

# ----------------------------------------------------------------------
# Make sure to set proper settings for python venv usage
ENV PATH="/home/minion/venv/bin:/home/minion/.local/bin:${PATH}"
# Configure entrypoint and base cmd for minion startup
ENTRYPOINT ["/home/minion/start.sh"]
CMD ["run"]
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Add metadata to the image
MAINTAINER Daniel Hofstetter<yio gmbh>
ARG YIO_MINION_PACKAGE=yio-minions
ARG YIO_MINION_VERSION=2.0.6

# Set label-schema labels
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.vendor="yio gmbh"

LABEL org.label-schema.name="${YIO_MINION_PACKAGE}"
LABEL org.label-schema.version="${YIO_MINION_VERSION}"
LABEL org.label-schema.description="A framework to execute external tasks with ease."
LABEL version="${YIO_MINION_VERSION}"
# ----------------------------------------------------------------------
