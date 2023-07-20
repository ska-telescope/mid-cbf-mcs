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

.. uml:: ../../diagrams/mid-cbf-scan-ops.puml

Commands for CbfController and CbfSubarray are below. 
For full details of MCS Controller see :ref:`CbfController`.
For full details of MCS Subarray see :ref:`CbfSubarray`.

CbfController Tango Commands
------------------------------

**CbfController.On** ()->Tuple[ResultCode, str]
*****************************************************

    Turns on the controller and it's subordinate devices

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfController.Off** ()->Tuple[ResultCode, str]
*****************************************************

    Turn off the controller and it's subordinate devices

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfController.Standby** ()->Tuple[ResultCode, str]
*****************************************************

    Put the CbfController into low power mode.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

CbfSubarray Tango Commands
----------------------------

**CbfSubarray.Abort** ()->Tuple[ResultCode, str]
****************************************************

    Abort subarray configuration or operation.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.AddReceptors** (*argin:List[str]*)->Tuple[ResultCode, str]
**************************************************************************

    Assign Receptors to this subarray. Turn subarray to ObsState = IDLE if previously no receptor is assigned.

        *Parameters:*    argin - list of receptors to add

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.ConfigureScan** (*argin: str*)->Tuple[ResultCode, str]
*******************************************************************************

    Change state to CONFIGURING. Configure attributes from input JSON. Subscribe events. Configure VCC, VCC subarray, FSP, FSP Subarray. publish output links.

        *Parameters:*   argin – The configuration as JSON formatted string.

        *Returns:*      A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*  (ResultCode, str)

**CbfSubarray.EndScan** ()->Tuple[ResultCode, str]
***************************************************

    End the scan

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.ObsReset** ()->Tuple[ResultCode, str]
****************************************************

    Reset subarray scan configuration.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.Off** ()->Tuple[ResultCode, str]
****************************************************

    Sets subarray power mode to off. Commands FSP <function mode> Subarrays to turn off.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.On** ()->Tuple[ResultCode, str]
****************************************************

    Sets subarray power mode to on. Commands FSP <function mode> Subarrays to turn on.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.RemoveAllReceptors** ()->Tuple[ResultCode, str]
****************************************************************

    Remove all receptors. Turn Subarray OFF if no receptors assigned

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.RemoveReceptors** (*argin:List[str]*)->Tuple[ResultCode, str]
*****************************************************************************

    Remove from list of receptors. Turn Subarray to ObsState = EMPTY if no receptors assigned. Uses RemoveReceptorsCommand class

        *Parameters:*    argin - list of receptor IDs to remove

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.Restart** ()->Tuple[ResultCode, str]
****************************************************

    Reset scan configuration and remove receptors.

        *Parameters:*    *None*

        *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*   (ResultCode, str)

**CbfSubarray.Scan** (*argin: str*)->Tuple[ResultCode, str]
********************************************************************************

    Start scanning

        *Parameters:*   argin (str) – The scan ID as JSON formatted string.

        *Returns:*  A tuple containing a return code and a string message indicating status. The message is for information purpose only.

        *Return type:*  (ResultCode, str)


   




