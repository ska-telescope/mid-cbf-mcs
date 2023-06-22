==================
CbfController 
==================

The ``CbfController`` Tango device controls its subordinate Tango devices: ``Fsp``, ``Vcc``, 
``CbfSubarray`` and ``TalonLRU``. It is responsible for turning these subordinate devices on 
and off, and putting the ``Fsp``,``Vcc`` and CbfSubarray devices in STANDBY mode. The 
CbfController also initiates the configuration of the Talon-DX boards. The ``CbfController`` 
device’s OnCommand triggers ``TalonDxComponentManager.configure_talons`` to be called which copies 
the device server binaries and FPGA bitstream to the Talon-DX boards, starts the HPS master 
device server and sends the configure command to each DsHpsMaster device.

CbfController Class
--------------------
.. autoclass:: ska_mid_cbf_mcs.controller.controller_device.CbfController
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

ControllerComponentManager Class
---------------------------------
.. autoclass:: ska_mid_cbf_mcs.controller.controller_component_manager.ControllerComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

TalonDxComponentManager Class
------------------------------
The ``TalonDxComponentManager`` is used to configure and start up Tango device servers 
on the Talon boards. These actions are performed during the On command of the ``CbfController``.
Note that these actions are not executed when the ``simulationMode`` of the ``CbfController`` is 
set to 1 (this is the default). Prior to sending the On command to the ``CbfController``, the 
``simulationMode`` should be set to 0 if it is desired to test the command with the Talon
boards in the loop.

.. autoclass:: ska_mid_cbf_mcs.controller.talondx_component_manager.TalonDxComponentManager
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
   :member-order: