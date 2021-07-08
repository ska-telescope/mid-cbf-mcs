FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:latest AS buildenv
FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:latest AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH
#install csp-lmc-common with dependencies
ADD pipconfig pipconfig
ENV PIP_CONFIG_FILE pipconfig/pip.conf
RUN python3 -m pip install -e . --user

CMD ["/venv/bin/python", "/app/tangods/CbfMaster/CbfMaster.py"]