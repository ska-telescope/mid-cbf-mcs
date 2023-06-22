=====================
CbfComponentManager
=====================

More details about the role of component managers can be found in the `SKA Tango Base Documentation 
<https://developer.skao.int/projects/ska-tango-base/en/latest/guide/component_managers.html>`_. In the Mid.CBF MCS 
each component has a Tango device class and a component manager class. The Tango device class updates its state model(s) 
(the ``op_state_model`` and\or ``obs_state_model``). The Tango device class does not directly communicate with its component, 
instead it tells its component manager class what to do by calling its methods. The component manager class directly interacts 
with its component. Its role is to establish communication with its component and monitor and control it.
An example of this Tango device and component manager interaction is shown in the diagram below. 

.. figure:: ../diagrams/component-manager-interactions.png
   :align: center

.. automodule:: ska_mid_cbf_mcs.component.component_manager


The MCS contains two types of Tango devices: observing and non-observing. 
Non-observing devices contain only an ``op_state_model`` while observing devices
contain both an ``op_state_model`` and ``obs_state_model``. As shown in the inheritance
diagram below, non-observing devices inherit from ``CbfComponentManager`` while observing
devices inherit from ``CbfComponentManager`` and ``CspObsComponentManager``. 

.. figure:: ../diagrams/component-manager-inheritance.png
   :align: center    

CbfComponentManager Class
---------------------------------
.. autoclass:: ska_mid_cbf_mcs.component.component_manager.CbfComponentManager
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order:


