.. Documentation

Fsp
======================================================

The ``Fsp`` Tango device is used for monitoring and control of a Frequency Slice 
Processor (FSP) during scan operation. An FSP device can be configured for processing 
of one of up to twenty-six frequency slices (depending on observational frequency 
band) and one of four function modes (CORR/PSS-BF/PST-BF/VLBI). Additionally, an 
FSP can be assigned to any number of subarrays with matching configurations.

Fsp Function Mode
-----------------

There are four function modes available for FSP scan configuration, each with a 
corresponding function mode capability and subarray device per FSP; furthermore, 
each FSP function mode subarray device corresponds to a unique pairing of one FSP 
with one subarray. Currently, one subarray and four FSPs are supported.

FSP Function Mode devices:

* Correlation (CORR): ``FspCorr`` and ``FspCorrSubarrayDevice``
* Pulsar Search Beamforming (PSS-BF): ``FspPss`` and ``FspPssSubarrayDevice``
* Pulsar Timing Beamforming (PST-BF): ``FspPst`` and ``FspPstSubarrayDevice``
* VLBI Beamforming (VLBI): ``FspVlbi`` and ``FspVlbiSubarrayDevice``
