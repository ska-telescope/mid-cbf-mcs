FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:latest AS buildenv
FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:latest AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

#install lmc-base-classes
USER root
RUN DEBIAN_FRONTEND=noninteractive pip3 install https://nexus.engageska-portugal.pt/repository/pypi/packages/lmcbaseclasses/0.4.0+5bdedbed/lmcbaseclasses-0.4.0+5bdedbed.tar.gz
CMD ["/venv/bin/python", "/app/tangods/CbfMaster/CbfMaster/CbfMaster.py", "master"]
