FROM artefact.skao.int/ska-tango-images-pytango-builder:9.4.1 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.4.1

ENV PATH=/home/tango/.local/bin:$PATH

RUN python3 -m pip install -r requirements.txt .
