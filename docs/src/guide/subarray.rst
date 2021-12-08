.. Documentation

CbfSubarray
======================================================

The ``CbfSubarray`` Tango device is used to monitor and control scan operation 
of a Mid.CBF receptor subarray. This device receives one configuration per scan, 
and a subarray may accept this scan configuration only after being assigned at 
least one receptor.

Receptor assignment
-------------------

Receptor assignment to a subarray is done before configuration for a scan. 
Receptor assignment is exclusive; receptors assigned to one subarray cannot 
belong to any other subarray. Up to 197 receptors can be assigned to one subarray; 
currently, there is only support for 4 receptors.

Scan configuration
------------------

Subarrays receive a scan configuration via an ASCII encoded JSON string. The scan 
configuration is validated for completeness and its parameters implemented as Tango 
device attributes; the subarray device will then also configure subordinate devices 
with the relevant parameters, including VCC, FSP and FSP-subarray devices.

.. figure:: ../diagrams/cbf-subarray-device.png
   :align: center
   
   MCS CbfSubarray Device Scan configuration
