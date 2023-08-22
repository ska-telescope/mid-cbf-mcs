FROM registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-builder:fd389036 as buildenv
FROM registry.gitlab.com/ska-telescope/ska-tango-images/ska-tango-images-pytango-runtime:fd389036

ENV PATH=/home/tango/.local/bin:$PATH

RUN python3 -m pip install docutils==0.19
RUN python3 -m pip install -r requirements.txt .
