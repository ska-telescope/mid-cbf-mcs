############
Change Log
############

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning http://semver.org/>`_.

Development
***********
* Added Abort and ObsReset command implementation for Vcc and 
  FspCorr/Pss/PstSubarray devices

0.10.17
********
* Increased hps master timeout to support DDR calibration health check
* Increased APC PDU outlet status polling interval to 20 seconds
* Add additional error catching to APC PDU driver

0.10.18
********
* Changed PDU config for LRU1 and LRU2

0.11.5
********
* Added InitSysParam command to controller
* Refactored reception utils to handle Dish VCC mapping
* Increased HPS master configure timeout

0.11.6
********
* Increase Artifacts PVC size to 1Gi (from 250Mi)