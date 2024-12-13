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

..
    Go to ska-mid-cbf-tdc-mcs/docs/src/ska-mcs-sphinx/ska-tables.py to find code that generates the below tables
..


CbfController Tango Commands
------------------------------

.. generate-command-table:: Controller


\* Schema for JSON string defined in the `Telescope Model - Mid.CBF schemas <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/midcbf/ska-mid-cbf.html>`_

CbfSubarray Tango Commands
----------------------------

.. generate-command-table:: Subarray

\* Schema for JSON string defined in the `Telescope Model - Mid.CBF schemas <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/midcbf/ska-mid-cbf.html>`_


Supported ConfigureScan Validation
------------------------------------

The telescope model will validate AA4 ranges, but due to ongoing development, 
MCS supports a subset of values for the given parameters.

.. generate-command-table:: Supported_Validation
