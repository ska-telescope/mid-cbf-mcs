.. Documentation

CbfController
======================================================

The ``CbfController`` Tango device controls its subordinate Tango devices: ``Fsp``, ``Vcc``, 
``CbfSubarray`` and ``TalonLRU``. It is responsible for turning these subordinate devices on 
and off, and putting the ``Fsp``,``Vcc`` and CbfSubarray devices in STANDBY mode. The 
CbfController also initiates the configuration of the Talon-DX boards. The ``CbfController`` 
device’s OnCommand triggers ``TalonDxComponentManager.configure_talons`` to be called which copies 
the device server binaries and FPGA bitstream to the Talon-DX boards, starts the HPS master 
device server and sends the configure command to each DsHpsMaster device.

