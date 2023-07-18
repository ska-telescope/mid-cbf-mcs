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

CbfController Commands
------------------------

On
************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.OnCommand
   :members:
   :undoc-members:
   :member-order:    
   :noindex:

Off
************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.OffCommand
   :members:
   :undoc-members:
   :member-order:
   :noindex:   

Standby
*****************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.StandbyCommand
   :members:
   :undoc-members:
   :member-order:
   :noindex:   

CbfSubarray Tango Commands
----------------------------

**AddReceptors** (*argin:List[str]*)->Tuple[ResultCode, str]
****************************************************************

    Assign Receptors to this subarray. Turn subarray to ObsState = IDLE if previously no receptor is assigned.

    *Parameters:*    argin - list of receptors to add

    *Returns:*       A tuple containing a return code and a string message indicating status. The message is for information purpose only.

    *Return type:*   (ResultCode, str)


.. automethod:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.AddReceptors
   :noindex:

Configure Scan
************************

.. automethod:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.ConfigureScan
   :noindex:

Scan
************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.ScanCommand
   :members:
   :undoc-members:
   :member-order:
   :noindex:
   
Remove Receptors
**************************

.. automethod:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveReceptors
   :noindex:

Remove All Receptors
******************************

.. automethod:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveAllReceptors
   :noindex:

End Scan
******************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.EndScanCommand
   :members:
   :undoc-members:
   :member-order:
   :noindex:
