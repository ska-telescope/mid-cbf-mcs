.. Documentation

Component Managers
======================================================

More details about the role of component managers can be found in the SKA Tango Base Documentation. In the Mid.CBF MCS 
each component has a Tango device class and a component manager class. The Tango device class updates its state model(s) 
(the ``op_state_model`` and\or ``obs_state_model``). The Tango device class does not directly communicate with its component, 
instead it tells its component manager class what to do by calling its methods. The component manager class directly interacts 
with its component. Its role is to establish communication with its component and monitor and control it.
An example of this Tango device and component manager interaction is shown in the diagram below. 


.. figure:: ../diagrams/component-manager-interactions.png
   :align: center