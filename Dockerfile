ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.4.3"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.4.3"

FROM ${BUILD_IMAGE} AS buildenv
FROM $BASE_IMAGE

USER root

RUN poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies and the app
RUN poetry install

USER tango

