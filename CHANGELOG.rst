############
Change Log
############

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning http://semver.org/>`_.

Development
***********
* Added Abort and ObsReset command implementation for Vcc and 
  FspCorr/Pss/PstSubarray devices

0.12.3
******
* CIP-1933 Fixed the group_proxy implementation

0.12.2
******
* CIP-1764 Added telmodel schema validation against the InitSysParam command 

0.12.1
*****
* Removed hardcoded input sample rate. 
* Changed fs_sample_rate to integer and in Hz
* Added check for missing Dish ID - VCC mapping during On command

0.12.0
*****
* Refactored controller OffCommand to issue graceful shutdown to HPS and reset subarray observing state

0.11.8
*****
* Created defaults for VCC internal gains values

0.11.7
*****
* Removes Delta F and K from VCC and replaces them with dish_sample_rate and num_samples_per_frame.

0.11.6
*****
* Increase Artifacts PVC size to 1Gi (from 250Mi)

0.11.5
********
* Added InitSysParam command to controller
* Refactored reception utils to handle Dish VCC mapping
* Increased HPS master configure timeout

0.11.4-0.11.2
*****
* Changed scan_id from string to integer

0.11.1
*****
* Fixed subarray GoToIdle to issue GoToIdle to VCC and FSP devices

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
