############
Change Log
############

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning http://semver.org/>`_.

Development
***********
* Added Abort and ObsReset command implementation for Vcc and 
  FspCorr/Pss/PstSubarray devices

0.11.7
******
* Removes Delta F and K from VCC and replaces them with dish_sample_rate and num_samples_per_frame.

0.11.6
*****
* Increase Artifacts PVC size to 1Gi (from 250Mi)

0.11.5
*****

0.11.4-0.11.2
********
* Changed scan_id from string to integer

0.11.1
*****

0.11.0
*****
* Added binderhub support
* Added tango operator support
* Changed files for ST-1771
  * Updated .make directory
  * Switched from requirements to poetry
  * Updated CI file to add new jobs for dev environment deployment
  * Charts were updated including templates
* Removed gemnasium scan job
* Removed legacy jobs

0.10.19
*****
* Fixed CAR release issues with 0.10.18 release
* No changes to codebase

0.10.18
*****
* Changed PDU config for LRU1 and LRU2

0.10.17
*****
* Increased hps master timeout to support DDR calibration health check
* Increased APC PDU outlet status polling interval to 20 seconds
* Add additional error catching to APC PDU driver
