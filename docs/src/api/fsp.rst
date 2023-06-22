==================
FSP 
==================

The ``Fsp`` Tango device is used for monitoring and control of a Frequency Slice 
Processor (FSP) during scan operation. An FSP device can be configured for processing 
of one of up to twenty-six frequency slices (depending on observational frequency 
band). Additionally, an FSP can be assigned to any number of subarrays with matching 
configurations.

FSP Function Mode
-----------------

There are four function modes available for FSP scan configuration, each with a 
corresponding function mode capability and subarray device per FSP; furthermore, 
each FSP function mode subarray device corresponds to a unique pairing of one FSP 
with one subarray. Currently, one subarray and four FSPs are supported.

FSP Function Mode Subarray devices:

* Correlation (CORR): ``FspCorrSubarray``
* Pulsar Search Beamforming (PSS-BF): ``FspPssSubarray``
* Pulsar Timing Beamforming (PST-BF): ``FspPstSubarray``
* VLBI Beamforming (VLBI): ``FspVlbiSubarray``

Fsp Device Class
---------------------------

.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_device.Fsp
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

FspComponentManager Class
---------------------------------
.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_component_manager.FspComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:   

FspCorrSubarray Class
---------------------------

.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_corr_subarray_device.FspCorrSubarray
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

FspCorrSubarrayComponentManager Class
-------------------------------------
.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_corr_subarray_component_manager.FspCorrSubarrayComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:   

FspPssSubarray Class
---------------------------

.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_pss_subarray_device.FspPssSubarray
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:   

FspPssSubarrayComponentManager Class
------------------------------------
.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_pss_subarray_component_manager.FspPssSubarrayComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

FspPstSubarray Class
---------------------------

.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_pst_subarray_device.FspPstSubarray
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

FspPstSubarrayComponentManager Class
------------------------------------
.. autoclass:: ska_mid_cbf_mcs.fsp.fsp_pst_subarray_component_manager.FspPstSubarrayComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

