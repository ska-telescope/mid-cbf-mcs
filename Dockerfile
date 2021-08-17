FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH

# uncomment commented lines in Dockerfile and in pip.conf to fix ssl cert verification issue (CIPA team - MDA network)
# ADD certs /usr/local/share/ca-certificates/
# ENV PIP_CONFIG_FILE pip.conf
USER root
# RUN update-ca-certificates

# workaround to install ska-tango-base v0.10 from gitlab until project can support v.0.11
RUN apt-get update && apt-get install -y git
USER tango
RUN python3 -m pip install -r requirements.txt .
RUN python3 -m pip install git+https://gitlab.com/ska-telescope/ska-tango-base@0.10.1#egg=ska-tango-base

CMD ["/venv/bin/python", "/app/tangods/CbfMaster/CbfMaster.py"]