FROM artefact.skao.int/ska-tango-images-pytango-builder:9.4.1 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.4.1

ENV PATH=/home/tango/.local/bin:$PATH

# uncomment following lines to fix pip ssl verification issue
################################################################################
ADD certs /usr/local/share/ca-certificates/
ENV PIP_CONFIG_FILE pip.conf
USER root
RUN update-ca-certificates
USER tango
################################################################################

RUN python3 -m pip install -r requirements.txt .
