############
Change Log
############

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning http://semver.org/>`_.

0.12.22
*******
* CIP-2050 Added temporary timeout in power_switch_device on/off to possible fix async issue
* CIP-1940 Updated configure_scan sequence diagram in ReadTheDocs

0.12.21
*******
* CIP-1356 Fixed CbfSubarray configure from READY failure

Development
***********
* Added Abort and ObsReset command implementation for Vcc and 
  FspCorr/Pss/PstSubarray devices

0.12.20
*******
* CIP-2050 Added additional logging for apsc_smnp_driver

0.12.19
*******
* CIP-2048 Added logging for idle_ctrl_word for visibility on intermittent type mismatch error

0.12.18
*******
* CIP-2067 Change epoch from int to float

0.12.17
*******
* CIP-2052 Fixed SlimLink disconnect_slim_tx_rx() by re-syncing idle_ctrl_words before initializing in loopback mode.

0.12.16
*******
* CIP-1898 Fix FSP subarrayMembership resetting after subarray GoToIdle

0.12.15
*******
* CIP-1915 Retrieve initial system parameters file from CAR through Telescope Model

0.12.14
*******
* CIP-1987 Updated default SlimLink config with new DsSlimTxRx FQDNs.
* CIP-2006 Updated Slim and SlimLink tests and documentation.

0.12.13
*******
* MAP-36 Add support for APC PDU Driver using SNMP Interface

0.12.12
*******
* CIP-1830 add back strict validation against the delay model epoch

0.12.11
*******
* CIP-1883 bumped engineering console version to 0.9.7, signal verification to 0.2.7
* CIP-2001 reverted fo_validity_interval internal parameter to 0.01

0.12.10
*******
* CIP-2006 Renamed all SlimMesh refs to just Slim

0.12.9
******
* CIP-1674 Logconsumer logs every message twice
* CIP-1853 Enhance system-tests to check ResultCode
* CIP-2012 MCS k8s test pipeline job output no longer includes code coverage table

0.12.8
******
* CIP-1769 Implement SLIM Tango device (mesh)
* CIP-1768 Implement SLIM Link Tango device

0.12.7
******
* CIP-1967 revert fo_validity_interval to 0.001 while CIP-2001 is being addressed

0.12.6
******
* CIP-1886 update vcc_component_manager._ready = False at the end of abort() 

0.12.5
******
* CIP-1870 decreased timeout for talon_board_proxy and influxdb client
* CIP-1967 Changed fo_validity_interval to 0.01 - it was incorrectly set to 0.001

0.12.4
******
* CIP-1957 Removed problematic vcc gain file (mnt/vcc_param/internal_params_receptor1_band1_.json)

0.12.3
******
* CIP-1933 Fixed the group_proxy implementation

0.12.2
******
* CIP-1764 Added telmodel schema validation against the InitSysParam command 

0.12.1
*****
* Removed hardcoded input sample rate
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
* Removes Delta F and K from VCC and replaces them with dish_sample_rate and num_samples_per_frame

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
