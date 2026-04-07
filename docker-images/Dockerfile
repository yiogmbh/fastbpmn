FROM ghcr.io/astral-sh/uv:python3.11-trixie-slim AS fastbpmn-base

# ----------------------------------------------------------------------
# Setup a non root user for execution
RUN useradd --create-home --shell /bin/bash fastbpmn
WORKDIR /home/fastbpmn
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Install libmagic1 (required for file mimetype detection)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libdmtx0b  \
    qpdf \
    && rm -rf /var/lib/apt/lists/*
# ----------------------------------------------------------------------

FROM fastbpmn-base AS build-python

WORKDIR /home/fastbpmn
ENV UV_PROJECT_ENVIRONMENT="/home/fastbpmn/venv"

# ----------------------------------------------------------------------
# Make sure to set proper settings for python and pip installation
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Install fastbpmn locally (from source) and all requirements
COPY . /build
RUN --mount=type=secret,id=uv_credentials,target=/root/.local/share/uv/credentials/credentials.toml \
     cd /build && uv sync --no-dev --no-editable && cd /home/fastbpmn

ENV PATH="/home/fastbpmn/venv/bin:$PATH"
# ----------------------------------------------------------------------


FROM fastbpmn-base AS fastbpmn


# ----------------------------------------------------------------------
# All following steps are performed as non-root user
USER fastbpmn

# Copy required files for regular version (dependent startup script)
COPY --chown=fastbpmn:fastbpmn docker-images/general/start.py /home/fastbpmn/start.py
COPY --chown=fastbpmn:fastbpmn docker-images/general/start.sh /home/fastbpmn/start.sh
COPY --chown=fastbpmn:fastbpmn docker-images/general/app /home/fastbpmn/app
COPY --chown=fastbpmn:fastbpmn --from=build-python /home/fastbpmn/venv /home/fastbpmn/venv

# ----------------------------------------------------------------------
# Make sure to set proper settings for python venv usage
ENV PATH="/home/fastbpmn/venv/bin:/home/fastbpmn/.local/bin:${PATH}"
# Configure entrypoint and base cmd for fastbpmn startup
ENTRYPOINT ["/home/fastbpmn/start.sh"]
CMD ["run"]
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Add metadata to the image
MAINTAINER Daniel Hofstetter<yio gmbh>

# Set label-schema labels
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.vendor="yio gmbh"

LABEL org.label-schema.name="${YIO_fastbpmn_PACKAGE}"
LABEL org.label-schema.version="${YIO_fastbpmn_VERSION}"
LABEL org.label-schema.description="A framework to execute external tasks with ease."
LABEL version="${YIO_fastbpmn_VERSION}"
# ----------------------------------------------------------------------
