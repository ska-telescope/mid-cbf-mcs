.. Documentation

Talon LRU
======================================================

The ``TalonLRU`` Tango device handles the monitor and control functionality 
for a single Talon LRU. A TalonLRU instance must therefore be created for each LRU. 
Currently this device only controls the power to the LRU via a proxy to the ``PowerSwitch`` 
device.

The operational state of this device always reflects the power state of the LRU.
If at least one of the PDU outlets connected to the LRU is switched on, the state 
of the ``TalonLRU`` device should be ON. If both outlets are switched off, then the
state should be OFF.

If the state of the outlets is not consistent with the state of the ``TalonLRU`` device
when it starts up (or when ``simulationMode`` of the ``PowerSwitch`` device changes),
the ``TalonLRU`` device transitions into a FAULT state. The power outlets must then
be manually switched to the expected startup state via some other method before resetting
the ``TalonLRU`` device.

The expected startup state of the device is OFF.

TalonLRU Device
---------------

.. autoclass:: ska_mid_cbf_mcs.talon_lru.talon_lru_device.TalonLRU
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:

TalonLRUComponentManager Class
------------------------------

.. autoclass:: ska_mid_cbf_mcs.talon_lru.talon_lru_component_manager.TalonLRUComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:
