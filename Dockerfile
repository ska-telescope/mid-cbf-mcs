FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 as buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH
#install csp-lmc-common with dependencies

# uncomment and edit pip.conf to fix ssl cert verification issue (CIPA team - MDA network)
# ADD pipconfig pipconfig
# ENV PIP_CONFIG_FILE pipconfig/pip.conf

RUN python3 -m pip install -r requirements.txt .

CMD ["/venv/bin/python", "/app/tangods/CbfMaster/CbfMaster.py"]