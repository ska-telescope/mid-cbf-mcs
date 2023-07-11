ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.35"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.22"
FROM $BUILD_IMAGE AS buildenv
FROM $BASE_IMAGE

ENV PATH=/home/tango/.local/bin:$PATH

RUN python3 -m pip install docutils==0.19 && \
    sed -i '/pytango/d' requirements.txt && \
    sed -i '/numpy/d' requirements.txt && \
    python3 -m pip install -r requirements.txt .
