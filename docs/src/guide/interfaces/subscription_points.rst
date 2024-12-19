Subscription Points
=====================

Mid CBF MCS subscribes to the following subscriptions points:

DelayModel
----------

As per the TMC-CSP Mid ICD, CSP requires Geometric delay as a fifth-order polynomial 
per receptor per Frequency Slice per polarization every 10 seconds. Regular updates during 
the scan are required. Keeping these requirements in mind, Geometric delay calculation 
is implemented in the TMC CSP Subarray Leaf Node. It should be delivered via the 
publish-subscribe mechanism, published on the "DelayModel" attribute of the CSP Subarray leaf node. 

..
    Go to ska-mid-cbf-tdc-mcs/docs/src/ska-mcs-sphinx/ska-tables.py to find code that generates the below table
..

.. generate-command-table:: Subscriptions