# Internal VCC Parameter Files

This directory contains parameter files that store internal parameters for each VCC in the system.
These parameters need to be passed down to each HPS-level VCC device, and are unique per receptor per band.
When the band is configured during a scan configuration, a parameter file is passed down to the respective
HPS VCC band device for configuration of the signal processing chain.

Currently the parameters tracked in these files are:
* VCC gain values per channel in the VCC

At a later time, the signal chain will add the ability to automatically calculate the gain values based on
some given set of restrictions. The parameter files must then be updated to store the latest set of gain
values so that if the system is restarted, the latest values are maintained and can be used. We may want
to consider some versioning / archiving scheme at that point if needed to track old values of the gains.
