ARG BUILD_IMAGE="registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-builder:9.4.2dev1-dev.c5e316570" as buildenv
ARG BASE_IMAGE="registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-runtime:9.4.2dev0-dev.c5e316570"

ENV PATH=/home/tango/.local/bin:$PATH

RUN python3 -m pip install docutils==0.19
RUN python3 -m pip install -r requirements.txt .
