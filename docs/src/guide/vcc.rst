.. Documentation

Mid.Cbf VCC Device Server (VccMulti)
===========================================

VCC Device
----------
The ``Vcc`` Tango device is used to control and monitor the functionality for a
single Talon-DX board that runs VCC functionality. This device communicates with
the top-level VCC device server running on the Talon-DX board to coordinate
setup and processing activites of low-level device servers.

The ``Vcc`` device can operated  in either simulation mode or not. When in simulation
mode (this is the default), simulator classes are used in place of communication
with the real Talon-DX Tango devices. This allows testing of the MCS without
any connection to the hardware.

.. figure:: ../diagrams/vcc-device.png
   :align: center
   
   MCS Vcc Device