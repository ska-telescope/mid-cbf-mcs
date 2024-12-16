TalonDxComponentManager Class
---------------------------------
The ``TalonDxComponentManager`` is used to configure and start up Tango device servers 
on the Talon boards. These actions are performed during the On command of the ``CbfController``.
Note that these actions are not executed when the ``simulationMode`` of the ``CbfController`` is 
set to 1 (this is the default). Prior to sending the On command to the ``CbfController``, the 
``simulationMode`` should be set to 0 if it is desired to test the command with the Talon
boards in the loop.

.. autoclass:: ska_mid_cbf_tdc_mcs.controller.talondx_component_manager.TalonDxComponentManager
   :members:
   :private-members:
   :undoc-members:
   :show-inheritance:
   :member-order:
