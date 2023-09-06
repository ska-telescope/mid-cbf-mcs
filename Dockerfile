FROM artefact.skao.int/ska-tango-images-pytango-builder:9.4.3 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.4.3

ENV PATH=/home/tango/.local/bin:$PATH

RUN apt update && apt install -y git
RUN python3 -m pip install docutils==0.19
RUN python3 -m pip install -r requirements.txt .
