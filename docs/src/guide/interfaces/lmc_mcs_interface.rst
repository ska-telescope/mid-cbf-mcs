LMC to MCS Interface
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

Init Command
**************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.InitCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:

On Command
************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.OnCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:

Off Command
************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.OffCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:   

Standby Command
*****************

.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController.StandbyCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:   

CbfSubarray Commands
------------------------

Add Receptor Command
*********************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.AddReceptorsCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:   
   :noindex:   

Configure Scan Command
************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.ConfigureScanCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:

Scan Command
************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.ScanCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:
   
Remove Receptors Command
**************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveReceptorsCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:

Remove All Receptors Command
******************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.RemoveAllReceptorsCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:

End Scan Command
******************************

.. autoclass:: ska_mid_cbf_mcs.subarray.subarray_device.CbfSubarray.EndScanCommand
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
   :noindex:
