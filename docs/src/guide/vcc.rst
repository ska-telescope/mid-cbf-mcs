.. Documentation

Vcc
======================================================

The ``Vcc`` Tango device monitors and controls a Very Course Channelizer (VCC) during scan operation. 
Each VCC receives and processes input from one receptor, and can produce 200 MHz frequency slices and 
300 MHz search windows. The number of frequency slices produced depends on the frequency band. These 
data products can be forwarded to any FSP.  

Subarray Membership
---------------------------

Each VCC belongs to one subarray. The ``Vcc`` device’s subarray membership is assigned by the ``CbfSubarray`` 
Tango device’s ``AddReceptorsCommand``.

Frequency Bands
---------------------------
The ``Vcc`` device has four subordinate Tango devices representing the frequency bands: ``VccBand1And2``, 
``VccBand3``, ``VccBand4`` and ``VccBand5``. The VCC can only process data from one band at a time. The 
``Vcc`` device is responsible for turning on and off one of these band devices and disabling the rest, 
via its TurnOnBandDevice and TurnOffBandDevice commands. When active the enabled band device is in 
operational state ``ON`` while the remaining bands are in operational state ``DISABLE``.