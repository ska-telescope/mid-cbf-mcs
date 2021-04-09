FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:9.3.1 AS buildenv
FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:9.3.1 AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

# install lmc-base-classes

# USER root
# RUN DEBIAN_FRONTEND=noninteractive pip3 install https://nexus.engageska-portugal.pt/repository/pypi/packages/ska-logging/0.2.1/ska_logging-0.2.1.tar.gz
# RUN DEBIAN_FRONTEND=noninteractive pip3 install https://nexus.engageska-portugal.pt/repository/pypi/packages/lmcbaseclasses/0.4.1+14ff4f1b/lmcbaseclasses-0.4.1+14ff4f1b.tar.gz
# CMD ["/venv/bin/python", "/app/tangods/CbfMaster/CbfMaster/CbfMaster.py", "master"]



ENV PATH=/home/tango/.local/bin:$PATH
#install csp-lmc-common with dependencies
RUN python3 -m pip install -e .[emulator] --user --extra-index-url https://nexus.engageska-portugal.pt/repository/pypi/simple

CMD ["/venv/bin/python", "/app/csp_lmc_common/CspMaster.py" ]