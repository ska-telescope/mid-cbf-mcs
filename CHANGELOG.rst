############
Change Log
############

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning http://semver.org/>`_.

UNRELEASED CHANGES
******************
* CIP-2799 Refactored wait_for_blocking_results to verify all incoming events
* CIP-2966 fixed SPEAD descriptor not ready before Scan under certain conditions
* CIP-2911 fixed bad error message appending in controller Off command
* CIP-2840 talon fans monitoring
  * added hasFanControl attribute to talon board devices to indicate if the board has control over fans
  * added fansRpm attribute to talon board devices
  * fixed bugs affecting talon board device initialization and influxdb queries
  * updated FPGA die voltage labels to be more descriptive
  * updated FPGA die voltage warning and alarm range according to stratix10 documentation
* CIP-2956 CbfSubarray now sends all previously assigned FSPs to IDLE at the top of ConfigureScan
* CIP-2917 Add optional configurable timeout for LRC wait thread; applied to HPS Master timeout
* CIP-2780 added 100g ethernet monitoring on talon board devices
* CIP-3028 Updated hw config after systems room re-organization.
* CIP-3034 Removed parallelization for LRU On and Off command queuing to work better with the ST PDU that is now in use.
* CIP-2549 Controller sets unused subdevices to AdminMode.NOT_FITTED
* CIP-2965 talondx-config generates in the beginning of integration test
* SKB-499 added attribute pingResult to talon board devices. Added missing warning/alarm values.
* CIP-2828 Added attribute lastHpsScanConfiguration for output configuration string and validation tests.

1.0.0
******
* CIP-1924 Upgrade to ska-tango-base v1.0.0
  * Created base classes for observing and non-observing devices (CbfObsDevice, CbfDevice) and component managers (CbfObsComponentManager, CbfComponentManager)
    * CbfObsDevice implements reduced subarray ObsState model, removing EMPTY and RESOURCING states for non-subarray devices.
  * Converted base component managers to inherit from TaskExecutorComponentManager
  * Converted the following commands/methods to queued LRCs/submitted tasks:
    * start_communicating
    * CbfController: On, Off, InitSysParam
    * CbfSubarray: update_sys_param, AddReceptors, RemoveReceptors, RemoveAllReceptors, ConfigureScan, Scan, EndScan, GoToIdle, Abort, ObsReset, Restart
    * Vcc: ConfigureBand, ConfigureScan, Scan, EndScan, GoToIdle, Abort, ObsReset
    * Fsp: SetFunctionMode, AddSubarrayMembership, RemoveSubarrayMembership
    * FspCorrSubarray: ConfigureScan, Scan, EndScan, GoToIdle, Abort, ObsReset
    * Slim: On, Off, Configure
    * SlimLink: ConnectTxRx, DisconnectTxRx
    * TalonLRU: On, Off
    * PowerSwitch: TurnOnOutlet, TurnOffOutlet
  * Removed the following commands:
    * Standby command removed across the board
    * CbfSubarray: On, Off
    * Vcc: On, Off
    * Fsp: On, Off
    * FspCorrSubarray: On, Off
    * TalonBoard: On, Off
  * Improvements in control flow:
    * Only Tango Devices that are directly controlling hardware can receive ON/OFF commands e.g. TalonLRU, and not Vcc
    * In  Tango Devices that do not receive ON/OFF commands, once communication with the component is established the OpState becomes ON. This is all achieved when start_communicating method is called as part of setting the Tango Device's AdminMode to ONLINE. In these cases, essentially ON means the device is communicating with it's subordinate device.
    * Moved AdminMode control of obs devices (Vcc, Fsp, FspCorrSubarray) from CbfController to CbfSubarray, during the following subarray commands:
      * Vcc AdminMode ONLINE/OFFLINE during AddReceptors/RemoveReceptors
      * Fsp AdminMode ONLINE/OFFLINE during ConfigureScan/GoToIdle
      * FspCorrSubarray ONLINE/OFFLINE set by Fsp during ConfigureScan/GoToIdle
    * State changing callbacks consistently use locks to avoid race conditions.
      * Component managers do not update state machines directly; only callbacks (implemented at the device level) are passed to the component managers.
  * Improvements in tests:
    * More thorough unit tests provide better low-level coverage for individual devices, including failure mechanisms.
    * Redundant subordinate device integration tests deprecated in favour of more comprehensive and holistic tests only at the highest levels of MCS (Controller and Subarray).
    * ska-tango-testing better leveraged to align our testing framework with the rest of the SKAO:
      * ska_tango_testing.context basis for unit testing harness
      * TangoEventTracer used along with custom defined change event assertions to validate event-driven device behaviour.

* CIP-2732 Added supported interface validation and documentation updates
  * Added validation for supported schema versions specified in the interface parameter for commands in MCS.
  * Added sphinx directive to generate tables for documentation
* CIP-2616 MCS ADR-99 Scan Configuration Validation Updates
  * Abstracted out the Scan Configuration Validation in Subarray into a separate class  
  * Updated the Validations and added new validations to support ADR-99/v4.1 Interface Changes
  * Refer to new MCS restrictions here: https://confluence.skatelescope.org/display/SE/Validation+of+Scan+Configuration+against+Supported+Configurations

* CIP-2504 Updated for mid.cbf CSP ConfigureScan 3.0 telescope model changes
  * Removed validation for tdc fields (removed from telescope model)
  * Removed validation for doppler_phase_corr_subscription_point (removed from
    telescope model)
  * Removed check for existence of delay_model_subscription (mandatory in telmodel)
  * Removed validation and setting zoom_factor and zoom_window_tuning

    * Removed from telescope model
    * Class properties remain, to be removed in base class update
    * zoom_factor set to 0 for downstream HPS config, this will be set later
      when zoom is implemented from the channel_width parameter introduced in 
      ADR-99

  * Added cross validation for cbf.fsp.output_port for the incoming ConfigureScan
  * Removed setting fsp subarray values from parameters removed from schema
  * Updated ConfigureScan unit test data to interface 3.0 
  * Updated output_port default value to expanded 2-tuple format

0.15.2
******
* CIP-2560 Moved visibility transport logic from FSP App to VisibilityTransport class. Multi-FSP support.
* CIP-2553 Reduced number of pods in MCS deployment
* CIP-2447 Added FpgaDieVoltage[0-6] Attributes in TalonBoard Device to read from the FPGA Die Voltage Sensors
* MAP-115 Updated MCS overview Taranta dashboard to include more info LRUs, sim mode and updates to the DISH ID
* MAP-116 Change initial board IP loading so it is set to an explicitly placeholder value until a HW config file is applied
* CIP-2604 Fixes issue where unused Talon times-out while trying to set SimulationMode in MCS's TalonBoard during Controller's On Command
* CIP-2365 Fixing shutdown order to fix off command failure, logging warning instead of error when talon board fails to turn off

0.15.1
******
* MAP-69 Removing old ec-bite and ec-deployer pods from MCS deployment
         and bumping EC to a version that integrates the new pods.

0.15.0
******
* CIP-2335 Migrated SlimTest From Engineering Console to MCS's Slim Device
* CIP-2396 Fixed Read the Docs Build Issues on MCS

0.14.2
******
* CIP-2418 Fix On command timeout by clearing talons with a script
* CIP-2416 Decoupled LRU ON and clearing talon 

0.14.1 (0.14.0: DO NOT USE)
******
* CIP-2257 Update to validate TMC-published delay model JSON data against
  schema version 3.0 (https://schema.skao.int/ska-mid-csp-delaymodel/3.0)

0.13.3
******
* CIP-1983 Added talon reboot to ON sequence to stop power cycling

0.13.2
******
* REL-1345: STFC cluster domain name change
* Updated ska-telmodel version to allow for duplicate k values

0.13.1
******
* CIP-2238/REL-1337: bumped engineering console version

0.13.0
******
* CIP-2238: Internally, MCS no longer refers to dishes/DISH IDs as receptors/receptor IDs, 
  and the distinction has been made when those integer indices actually refer to VCC IDs

0.12.28
*******
* CIP-2306: Implemented is_ConfigureScan_allowed() to enforce state model for ConfigureScan.
* STS-548: Updated k8s.mk to collect k8s-test logs in logs/ artifact folder after pipeline runs.

0.12.27
*******
* CIP-2279: Overrode is_allowed for CbfController On/Off so these commands can't be called when already in execution.
* CIP-2227: Refactored flow of CbfController start_communicating in setting sub-element adminMode to ONLINE

0.12.26
*******
* CIP-2105: Fixed FSP error from trying to remove group proxy from IDLE state.

0.12.25
*******
* CIP-1979: Updated SubarrayComponentManager to assign channel_offset=1 in FSP configuration when LMC does not define one.

0.12.24
*******
* CIP-1849: Implemented obsfault for Vcc and Fsp<func> Subarray

0.12.23
*******
* CIP-1940: Updated ConfigureScan sequence diagram
* CIP-2048: Added ping check and ICW regeneration condition to SlimLink

0.12.22
*******
* CIP-2050 Added temporary timeout in power_switch_device on/off to possible fix async issue

0.12.21
*******
* CIP-1356 Fixed CbfSubarray configure from READY failure

Development
***********
* Added Abort and ObsReset command implementation for Vcc and 
  FspCorr/Pss/PstSubarray devices

0.12.20
*******
* CIP-2050 Added additional logging for apc_snmp_driver

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
* CIP-1674 LogConsumer logs every message twice
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
