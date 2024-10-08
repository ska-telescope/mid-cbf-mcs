FROM artefact.skao.int/ska-tango-images-pytango-builder:9.5.0 AS buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.5.0 AS runtime
# The below line fixes an issue where `make oci-build` gives the error: ERROR: failed to solve: cannot copy from stage "buildenv", it needs to be defined before current stage "runtime"
COPY --from=buildenv . .


USER root

RUN poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY pyproject.toml poetry.lock* ./

# Install runtime dependencies and the app
RUN poetry install --only main

USER tango
