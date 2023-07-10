ARG BUILD_IMAGE="registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-builder:9.4.2dev1-dev.c5e316570"
ARG BASE_IMAGE="registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-runtime:9.4.2dev0-dev.c5e316570"
FROM $BUILD_IMAGE AS buildenv
FROM $BASE_IMAGE

ENV PATH=/home/tango/.local/bin:$PATH

RUN python3 -m pip install docutils==0.19 && \
    sed -i '/pytango/d' requirements.txt && \
    sed -i '/numpy/d' requirements.txt && \
    python3 -m pip install -r requirements.txt .
