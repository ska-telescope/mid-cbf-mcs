LMC to MCS
=====================

MCS provides commands and attributes to turn MCS on and off (through the CBF Controller)
as well as commands needed to configure and execute scans through the subarrays. (CBF Subarray)

The sequence diagram below shows the interactions between LMC and MCS to assign 
receptors to a subarray, configure a scan, and run a scan. 
It shows configuration of one Mid.CBF subarray
followed by running a scan on that subarray. It ends with no receptors assigned
to the subarray. The calls to write the frequency offset K and frequency offset
delta F values only need to be written when there are updates to the values. They must
be written to the CBF Controller before the scan configuration.

For full details of MCS Controller see :ref:`CbfController`.

For full details of MCS Subarray see :ref:`CbfSubarray`.

.. uml:: ../../diagrams/mid-cbf-scan-ops.puml

CbfController Tango Commands
------------------------------

+--------------+---------------+--------------------+--------------------------------------------------------+
| Command      | Parameters    | Return type        | Action                                                 |
+==============+===============+====================+========================================================+
| Off          | None          | (ResultCode, str)  | Turn off the controller and subordinate devices        |
+--------------+---------------+--------------------+--------------------------------------------------------+
| InitSysParam | str           | (ResultCode, str)  | Initialize Dish ID to VCC ID mapping and k values      |
+--------------+---------------+--------------------+--------------------------------------------------------+
| Standby      | None          | (ResultCode, str)  | Put in low power mode                                  |
+--------------+---------------+--------------------+--------------------------------------------------------+
| On           | None          | (ResultCode, str)  | Turn on the controller and subordinate devices         |
+--------------+---------------+--------------------+--------------------------------------------------------+

CbfSubarray Tango Commands
----------------------------

+----------------------+---------------+--------------------+-------------------------------------------+
| Command              | Parameters    | Return type        | Action                                    |
+======================+===============+====================+===========================================+
| Abort                | None          | (ResultCode, str)  | Abort subarray configuration or operation |
+----------------------+---------------+--------------------+-------------------------------------------+
| AddReceptors         | List[str]     | (ResultCode, str)  | | Assign receptors to this subarray       |
|                      |               |                    | | Turn subarray to ObsState = IDLE if no  |
|                      |               |                    | | receptor was previously assigned        |
+----------------------+---------------+--------------------+-------------------------------------------+
| ConfigureScan        | JSON str*     | (ResultCode, str)  | | Change state to configuring             |
|                      |               |                    | | Configure attributes from input JSON    |
|                      |               |                    | | Subscribe events                        |
|                      |               |                    | | Configure VCC, VCC subarray, FSP,       |
|                      |               |                    | | FSP Subarray. Publish output links.     |
+----------------------+---------------+--------------------+-------------------------------------------+
| EndScan              | None          | (ResultCode, str)  | End the scan                              |
+----------------------+---------------+--------------------+-------------------------------------------+
| ObsReset             | None          | (ResultCode, str)  | Reset subarray scan configuration         |
+----------------------+---------------+--------------------+-------------------------------------------+
| Off                  | None          | (ResultCode, str)  | | Set subarry power mode to off.          |
|                      |               |                    | | Commands FSP<function mode> Subarrays   |
|                      |               |                    | | to turn off                             |
+----------------------+---------------+--------------------+-------------------------------------------+
| On                   | None          | (ResultCode, str)  | | Set subarry power mode to on.           |
|                      |               |                    | | Commands FSP<function mode> Subarrays   |
|                      |               |                    | | to turn on                              |
+----------------------+---------------+--------------------+-------------------------------------------+
| RemoveAllReceptors   | None          | (ResultCode, str)  | | Remove all receptors                    |
|                      |               |                    | | Turns Subarray off if no receptors are  |
|                      |               |                    | | assigned                                |
+----------------------+---------------+--------------------+-------------------------------------------+
| RemoveReceptors      | List[str]     | (ResultCode, str)  | | Remove receptors in input list          |
|                      |               |                    | | Turns Subarray to ObsState=EMPTY if no  |
|                      |               |                    | | receptors assigned                      |
+----------------------+---------------+--------------------+-------------------------------------------+
| Restart              | None          | (ResultCode, str)  | | Reset scan configuration and            |
|                      |               |                    | | remove receptors                        |
+----------------------+---------------+--------------------+-------------------------------------------+
| Scan                 | JSON str*     | (ResultCode, str)  | Start scanning                            |
+----------------------+---------------+--------------------+-------------------------------------------+
   
* Schema for JSON string defined in the `Telescope Model - Mid.CBF schemas <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-mid-cbf.html>`_



