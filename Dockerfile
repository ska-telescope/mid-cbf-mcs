FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH

# uncomment following lines and in pip.conf to fix ssl verification issue
################################################################################
# ADD certs /usr/local/share/ca-certificates/
# ENV PIP_CONFIG_FILE pip.conf
# USER root
# RUN update-ca-certificates
# USER tango
################################################################################

RUN python3 -m pip install -r requirements.txt .

# CMD ["CbfController"]