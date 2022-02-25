FROM ska-tango-images-pytango-builder:latest as buildenv
FROM ska-tango-images-pytango-runtime:latest

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH

# uncomment following lines to fix pip ssl verification issue
################################################################################
# ADD certs /usr/local/share/ca-certificates/
# ENV PIP_CONFIG_FILE pip.conf
# USER root
# RUN update-ca-certificates
# USER tango
################################################################################

RUN python3 -m pip install -r requirements.txt .
