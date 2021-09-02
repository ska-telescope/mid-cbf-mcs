FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 as buildenv

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

ENV PATH=/home/tango/.local/bin:$PATH

# uncomment following lines in Dockerfile and in pip.conf to fix ssl cert verification issue (CIPA team - MDA network)
# ADD certs /usr/local/share/ca-certificates/
# ENV PIP_CONFIG_FILE pip.conf
# USER root
# RUN update-ca-certificates
# USER tango

COPY requirements.txt ./
RUN python3 -m pip install -r /requirements.txt --prefix /app

# second build stage to minimize final size
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10

# point to built libraries - to be copied below
ENV PYTHONPATH=/app/venv/lib/python3.7/site-packages

# do not buffer stdout - so we get the logs
ENV PYTHONUNBUFFERED=1

# copy the built library dependencies from the builder stage
COPY --from=buildenv /app /app

# CMD ["/venv/bin/python", "/app/src/ska_mid_cbf_mcs/controller/controller.py"]
