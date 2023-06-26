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

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.On
   :members:
   :undoc-members:
   :member-order:
   :noindex:

Off
************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.Off
   :members:
   :undoc-members:
   :member-order:
   :noindex:   

Standby
*****************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.Standby
   :members:
   :undoc-members:
   :member-order:
   :noindex:   

CbfSubarray Commands
------------------------

Add Receptors
*********************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.AddReceptors
   :members:
   :undoc-members:
   :member-order:   
   :noindex:   

Configure Scan
************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.ConfigureScan
   :members:
   :undoc-members:
   :member-order:
   :noindex:

Scan
************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.Scan
   :members:
   :undoc-members:
   :member-order:
   :noindex:
   
Remove Receptors
**************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveReceptors
   :members:
   :undoc-members:
   :member-order:
   :noindex:

Remove All Receptors
******************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveAllReceptors
   :members:
   :undoc-members:
   :member-order:
   :noindex:

End Scan
******************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.EndScan
   :members:
   :undoc-members:
   :member-order:
   :noindex:
