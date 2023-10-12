"""
This module provides an abstract component manager for SKA Tango base devices.

The basic model is:

* Every Tango device has a *component* that it monitors and/or
  controls. That component could be, for example:

  * Hardware such as an antenna, APIU, TPM, switch, subrack, etc.

  * An external software system such as a cluster manager

  * A software routine, possibly implemented within the Tango device
    itself

  * In a hierarchical system, a pool of lower-level Tango devices.

* A Tango device will usually need to establish and maintain a
  *connection* to its component. This connection may be deliberately
  broken by the device, or it may fail.

* A Tango device *controls* its component by issuing commands that cause
  the component to change behaviour and/or state; and it *monitors* its
  component by keeping track of its state.
"""
from ska_tango_base.control_model import PowerMode

NUM_COUNTERS = 7
NUM_REG_COUNTERS_RX = 4
NUM_COUNTERS_TX = 3
BLOCK_LOST_COUNT_INDEX = 4
CDR_LOST_COUNT_INDEX = 5
NUM_LOST_COUNTERS = 2


class SlimLinkComponentManager(CbfComponentManager):
    """
    An abstract base class for a component manager for SKA Tango devices.

    It supports:

    * Maintaining a connection to its component

    * Controlling its component via commands like Off(), Standby(),
      On(), etc.

    * Monitoring its component, e.g. detect that it has been turned off
      or on
    """
    
    @property
    def tx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the tx device the link is associated with.

        :return: the tx device name
        """
        return self._tx_device_name

    @tx_device_name.setter
    def tx_device_name(
        self: SlimLinkComponentManager, tx_device_name: str
    ) -> None:
        """
        Set the tx device name value.

        :param tx_device_name: The tx device name
        """
        self._tx_device_name = tx_device_name

    @property
    def rx_device_name(self: SlimLinkComponentManager) -> str:
        """
        The name of the rx device the link is associated with.

        :return: the rx device name
        """
        return self._rx_device_name

    @rx_device_name.setter
    def rx_device_name(
        self: SlimLinkComponentManager, rx_device_name: str
    ) -> None:
        """
        Set the rx device name value.

        :param rx_device_name: The rx device name
        """
        self._rx_device_name = rx_device_name


    def __init__(
        self:SlimLinkComponentManager,
        tx_device_name: str,
        rx_device_name: str,
        logger: logging.Logger,
        push_change_event_callback: Optional[Callable],
        communication_status_changed_callback: Callable[
            [CommunicationStatus], None
        ],
        component_power_mode_changed_callback: Callable[[PowerMode], None],
        component_fault_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialise a new ComponentManager instance.

        :param tx_device_name: a string containing the tx device's fqdn
        :param rx_device_name: a string containing the rx device's fqdn
        :param logger: a logger for this object to use
        :param push_change_event_callback: method to call when the base classes
            want to send an event
        :param communication_status_changed_callback: callback to be
            called when the status of the communications channel between
            the component manager and its component changes
        :param component_power_mode_changed_callback: callback to be
            called when the component power mode changes
        :param component_fault_callback: callback to be called in event of
            component fault
        """
        self.connected = False
        
        self._tx_device_name = tx_device_name
        self._rx_device_name = rx_device_name
        
        self._tx_device_proxy = None
        self._rx_device_proxy = None
        
        super().__init__(
            logger=logger,
            push_change_event_callback=push_change_event_callback,
            communication_status_changed_callback=communication_status_changed_callback,
            component_power_mode_changed_callback=component_power_mode_changed_callback,
            component_fault_callback=component_fault_callback,
            obs_state_model=None,
        )
        
        self._logger.info("Linking {tx_device_name} to {rx_device_name}")


    def start_communicating(self: SlimLinkComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""

        if self.connected:
            self._logger.info("Already communicating.")
            return

        super().start_communicating()
        
        try:
            self._tx_device_proxy = CbfDeviceProxy(
                fqdn=self._tx_device_fqdn, logger=self._logger
            )
            self._rx_device_proxy = CbfDeviceProxy(
                fqdn=self._rx_device_fqdn, logger=self._logger
            )
        except tango.DevFailed:
            self.update_component_fault(True)
            self._logger.error("Error in proxy connection")
            return
            
        self.connected = True
        self.update_communication_status(CommunicationStatus.ESTABLISHED)
        self.update_component_power_mode(PowerMode.ON)
        self.update_component_fault(False)


    def stop_communicating(self: SlimLinkComponentManager) -> None:
        """Stop communication with the component."""
        super().stop_communicating()
        self.update_component_power_mode(PowerMode.OFF)
        self.connected = False


    @property
    def is_communicating(self):
        """
        Return whether communication with the component is established.

        For example:

        * If communication is over a connection, are you connected?
        * If communication is via event subscription, are you
          subscribed, and is the event subsystem healthy?
        * If you are polling the component, is the polling loop running,
          and is the component responsive?

        :return: whether there is currently a connection to the
            component
        :rtype: bool
        """
        raise NotImplementedError("BaseComponentManager is abstract.")

    @property
    def power_mode(self):
        """
        Power mode of the component.

        :return: the power mode of the component
        """
        raise NotImplementedError("BaseComponentManager is abstract.")

    @property
    def faulty(self):
        """
        Whether the component is currently faulting.

        :return: whether the component is faulting
        """
        raise NotImplementedError("BaseComponentManager is abstract.")

    def off(self):
        """Turn the component off."""
        raise NotImplementedError("BaseComponentManager is abstract.")

    def standby(self):
        """Put the component into low-power standby mode."""
        raise NotImplementedError("BaseComponentManager is abstract.")

    def on(self):
        """Turn the component on."""
        raise NotImplementedError("BaseComponentManager is abstract.")

    def reset(self):
        """Reset the component (from fault state)."""
        raise NotImplementedError("BaseComponentManager is abstract.")

    action_map = {
        PowerMode.OFF: "component_off",
        PowerMode.STANDBY: "component_standby",
        PowerMode.ON: "component_on",
    }

    def component_power_mode_changed(self, power_mode):
        """
        Handle notification that the component's power mode has changed.

        This is a callback hook.

        :param power_mode: the new power mode of the component
        :type power_mode:
            :py:class:`ska_tango_base.control_model.PowerMode`
        """
        action = self.action_map[power_mode]
        self.op_state_model.perform_action(action)

    def component_fault(self):
        """
        Handle notification that the component has faulted.

        This is a callback hook.
        """
        self.op_state_model.perform_action("component_fault")
