ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.2.0
FROM $BUILD_IMAGE AS build

ENV VIRTUAL_ENV=/app \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN set -xe; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3-venv; \
    python3 -m venv $VIRTUAL_ENV; \
    mkdir /build; \
    ln -s $VIRTUAL_ENV /build/.venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH

WORKDIR /build

# We install the dependencies and the application in two steps so that the
# dependency installation can be cached by the OCI image builder.  The
# important point is to install the dependencies _before_ we copy in src so
# that changes to the src directory to not result in needlessly reinstalling the
# dependencies.

# Installing the dependencies into /app here relies on the .venv symlink created
# above.  We use poetry to install the dependencies so that we can pass
# `--only main` to avoid installing dev dependencies.  This option is not
# available for pip.
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root --no-directory

# The README.md here must match the `tool.poetry.readme` key in the
# pyproject.toml otherwise the `pip install` step below will fail.
COPY README.md ./
COPY src ./src

# We use pip to install the application because `poetry install` is
# equivalent to `pip install --editable` which creates symlinks to the src
# directory, whereas we want to copy the files.
RUN pip install --no-deps .

# We don't want to copy pip into the runtime image
RUN pip uninstall -y pip

FROM $BASE_IMAGE

ENV VIRTUAL_ENV=/app
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --chown=tango:tango --from=build $VIRTUAL_ENV $VIRTUAL_ENV
ADD --chown=tango:tango mnt $VIRTUAL_ENV/mnt

WORKDIR $VIRTUAL_ENV