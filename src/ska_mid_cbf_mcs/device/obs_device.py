# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2024 National Research Council of Canada

"""
CbfObsDevice

Generic observing device for Mid.CBF
"""

from __future__ import annotations

from typing import Any, Callable, Optional, cast

from ska_control_model import (
    AdminMode,
    HealthState,
    ObsState,
    ObsStateModel,
    PowerState,
    ResultCode,
    SimulationMode,
)
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.obs.obs_device import SKAObsDevice
from tango import DebugIt
from tango.server import attribute, command, device_property
from transitions.extensions import LockedMachine as Machine

__all__ = ["CbfSubElementObsStateMachine", "CbfObsDevice", "main"]


class CbfSubElementObsStateMachine(Machine):
    """
    The observation state machine used by a generic Mid.CBF sub-element ObsDevice.

    NOTE: entirely cribbed from ska-csp-lmc-base CspSubElementObsStateMachine,
    to decouple MCS from their ska-tango-base version dependency

    Compared to the SKA Observation State Machine, it implements a
    smaller number of states, number that can be further decreased
    depending on the necessities of the different sub-elements.

    The implemented states are:

    * **IDLE**: the device is unconfigured.

    * **CONFIGURING_IDLE**: the device is unconfigured, but
      configuration is in progress.

    * **CONFIGURING_READY**: the device is configured, but configuration
      is in progress.

    * **READY**: the device is configured and is ready to perform
      observations

    * **SCANNING**: the device is performing the observation.

    * **ABORTING**: the device is processing an abort.

    * **ABORTED**: the device has completed the abort request.

    * **FAULT**: the device component has experienced an error from
      which it can be recovered only via manual intervention invoking a
      reset command that forces the device to the base state (IDLE).

    The actions supported divide into command-oriented actions and
    component monitoring actions.

    The command-oriented actions are:

    * **configure_invoked** and **configure_completed**: bookending the
      Configure() command, and hence the CONFIGURING state
    * **abort_invoked** and **abort_completed**: bookending the Abort()
      command, and hence the ABORTING state
    * **obsreset_invoked** and **obsreset_completed**: bookending the
      ObsReset() command, and hence the OBSRESETTING state
    * **end_invoked**, **scan_invoked**, **end_scan_invoked**: these
      result in reflexive transitions, and are purely there to indicate
      states in which the End(), Scan() and EndScan() commands are
      permitted to be run

    The component-oriented actions are:

    * **component_obsfault**: the monitored component has experienced an
      observation fault
    * **component_unconfigured**: the monitored component has become
      unconfigured
    * **component_configured**: the monitored component has become
      configured
    * **component_scanning**: the monitored component has started
      scanning
    * **component_not_scanning**: the monitored component has stopped
      scanning
    """

    def __init__(
        self, callback: Optional[Callable] = None, **extra_kwargs: Any
    ) -> None:
        """
        Initialise the model.

        :param callback: A callback to be called when the state changes
        :param extra_kwargs: Additional keywords arguments to pass to super class
            initialiser (useful for graphing)
        """
        self._callback = callback

        states = [
            "IDLE",
            "CONFIGURING_IDLE",  # device CONFIGURING but component is unconfigured
            "CONFIGURING_READY",  # device CONFIGURING and component is configured
            "READY",
            "SCANNING",
            "ABORTING",
            "ABORTED",
            "RESETTING",
            "FAULT",
        ]
        transitions = [
            {
                "source": "*",
                "trigger": "component_obsfault",
                "dest": "FAULT",
            },
            {
                "source": "IDLE",
                "trigger": "configure_invoked",
                "dest": "CONFIGURING_IDLE",
            },
            {
                "source": "CONFIGURING_IDLE",
                "trigger": "configure_completed",
                "dest": "IDLE",
            },
            {
                "source": "READY",
                "trigger": "configure_invoked",
                "dest": "CONFIGURING_READY",
            },
            {
                "source": "CONFIGURING_IDLE",
                "trigger": "component_configured",
                "dest": "CONFIGURING_READY",
            },
            {
                "source": "CONFIGURING_READY",
                "trigger": "configure_completed",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "end_invoked",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "component_unconfigured",
                "dest": "IDLE",
            },
            {
                "source": "READY",
                "trigger": "scan_invoked",
                "dest": "READY",
            },
            {
                "source": "READY",
                "trigger": "component_scanning",
                "dest": "SCANNING",
            },
            {
                "source": "SCANNING",
                "trigger": "end_scan_invoked",
                "dest": "SCANNING",
            },
            {
                "source": "SCANNING",
                "trigger": "component_not_scanning",
                "dest": "READY",
            },
            {
                "source": [
                    "IDLE",
                    "CONFIGURING_IDLE",
                    "CONFIGURING_READY",
                    "READY",
                    "SCANNING",
                    "RESETTING",
                ],
                "trigger": "abort_invoked",
                "dest": "ABORTING",
            },
            # Aborting implies trying to stop the monitored component
            # while it is doing something. Thus the monitored component
            # may send some events while in aborting state.
            {
                "source": "ABORTING",
                "trigger": "component_unconfigured",  # Abort() invoked on ObsReset()
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "component_configured",  # Configure() was just finishing
                "dest": "ABORTING",
            },
            {
                "source": ["ABORTING"],
                "trigger": "component_not_scanning",  # Aborting implies stopping scan
                "dest": "ABORTING",
            },
            {
                "source": ["ABORTING"],
                "trigger": "component_scanning",  # Abort() invoked as scan is starting
                "dest": "ABORTING",
            },
            {
                "source": "ABORTING",
                "trigger": "abort_completed",
                "dest": "ABORTED",
            },
            {
                "source": ["ABORTED", "FAULT"],
                "trigger": "obsreset_invoked",
                "dest": "RESETTING",
            },
            {
                "source": "RESETTING",
                "trigger": "component_unconfigured",  # Resetting implies deconfiguring
                "dest": "RESETTING",
            },
            {
                "source": "RESETTING",
                "trigger": "obsreset_completed",
                "dest": "IDLE",
            },
        ]
        super().__init__(
            states=states,
            initial="IDLE",
            transitions=transitions,
            after_state_change=self._state_changed,
            **extra_kwargs,
        )
        self._state_changed()

    def _state_changed(self) -> None:
        """
        State machine callback that is called every time the obs_state changes.

        Responsible for ensuring that callbacks are called.
        """
        if self._callback is not None:
            self._callback(self.state)


class CbfObsDevice(SKAObsDevice):
    """
    A generic base observing device for Mid.CBF.
    Extends SKAObsDevice to override certain key values.
    """

    # -----------------
    # Device Properties
    # -----------------

    DeviceID = device_property(dtype="uint16", default_value=1)

    # ----------
    # Attributes
    # ----------

    @attribute(dtype="uint16", doc="The observing device ID.")
    def deviceID(self: CbfObsDevice) -> int:
        """
        Read the device's ID.

        :return: the current DeviceID value
        """
        return self.DeviceID

    @attribute(
        dtype="uint64",
        doc="The scan identification number to be inserted in the output products.",
    )
    def scanID(self: CbfObsDevice) -> int:
        """
        Read the current scan ID of the device.

        :return: the current scan_id value
        """
        return self.component_manager.scan_id

    @attribute(
        dtype="str",
        doc="The configuration ID specified into the JSON configuration.",
    )
    def configurationID(self: CbfObsDevice) -> str:
        """
        Read the current configuration ID of the device.

        :return: the current config_id value
        """
        return self.component_manager.config_id

    @attribute(dtype="str", doc="The last valid scan configuration.")
    def lastScanConfiguration(self: CbfObsDevice) -> str:
        """
        Read the last valid scan configuration of the device.

        :return: the current _last_scan_configuration value
        """
        return self._last_scan_configuration

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    def simulationMode(self: CbfObsDevice) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: CbfObsDevice, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.debug(f"Writing simulationMode to {value}")
        self._simulation_mode = value
        self.component_manager.simulation_mode = value

    @attribute(dtype=AdminMode, memorized=True, hw_memorized=True)
    def adminMode(self: CbfObsDevice) -> AdminMode:
        """
        Read the Admin Mode of the device.

        It may interpret the current device condition and condition of all managed
         devices to set this. Most possibly an aggregate attribute.

        :return: Admin Mode of the device
        """
        return self._admin_mode

    @adminMode.write  # type: ignore[no-redef]
    def adminMode(self: CbfObsDevice, value: AdminMode) -> None:
        """
        Set the Admin Mode of the device.

        :param value: Admin Mode of the device.

        :raises ValueError: for unknown adminMode
        """
        if value == AdminMode.NOT_FITTED:
            self.admin_mode_model.perform_action("to_notfitted")
        elif value == AdminMode.OFFLINE:
            self.component_manager.stop_communicating()
        elif value == AdminMode.ENGINEERING:
            self.admin_mode_model.perform_action("to_engineering")
            self.component_manager.start_communicating()
        elif value == AdminMode.ONLINE:
            self.component_manager.start_communicating()
        elif value == AdminMode.RESERVED:
            self.admin_mode_model.perform_action("to_reserved")
        else:
            raise ValueError(f"Unknown adminMode {value}")

    # ----------
    # Callbacks
    # ----------

    def _component_state_changed(
        self: CbfObsDevice,
        fault: Optional[bool] = None,
        power: Optional[PowerState] = None,
        resourced: Optional[bool] = None,
        configured: Optional[bool] = None,
        scanning: Optional[bool] = None,
        obsfault: Optional[bool] = None,
    ) -> None:
        super()._component_state_changed(fault=fault, power=power)

        if resourced is not None:
            if resourced:
                self.obs_state_model.perform_action("component_resourced")
            else:
                self.obs_state_model.perform_action("component_unresourced")
        if configured is not None:
            if configured:
                self.obs_state_model.perform_action("component_configured")
            else:
                self.obs_state_model.perform_action("component_unconfigured")
        if scanning is not None:
            if scanning:
                self.obs_state_model.perform_action("component_scanning")
            else:
                self.obs_state_model.perform_action("component_not_scanning")
        if obsfault is not None:
            if obsfault:
                self.obs_state_model.perform_action("component_obsfault")
            # NOTE: to recover from obsfault, ObsReset or Restart must be invoked

    def _obs_command_running(
        self: CbfObsDevice, hook: str, running: bool
    ) -> None:
        """
        Callback provided to component manager to drive the obs state model into
        transitioning states during the relevant command's submitted thread.

        :param hook: the observing command-specific hook
        :param running: True when thread begins, False when thread completes
        """
        action = "invoked" if running else "completed"
        self.obs_state_model.perform_action(f"{hook}_{action}")

    def _update_obs_state(self: CbfObsDevice, obs_state: ObsState) -> None:
        """
        Perform Tango operations in response to a change in obsState.

        This helper method is passed to the observation state model as a
        callback, so that the model can trigger actions in the Tango
        device.

        Overridden here to supply new ObsState value to component manager property

        :param obs_state: the new obs_state value
        """
        self.logger.debug(f"ObsState updating to {ObsState(obs_state).name}")
        super()._update_obs_state(obs_state=obs_state)
        if hasattr(self, "component_manager"):
            self.component_manager.obs_state = obs_state

    def _admin_mode_perform_action(self: CbfObsDevice, action: str) -> None:
        """
        Callback provided to perform an action on the state model from
        component manager.

        :param action: an action, as given in the transitions table
        """
        self.admin_mode_model.perform_action(action)

    # TODO: CIP-3262 This method is overridden from SkaBaseDevice.
    # The parent implementation includes the event pushing calls that have
    # been commented out here because in this device it causes the pod to
    # crash. Once the bug has been squashed, this overriden method can be
    # removed to allow the original implementation to push events again.
    def _update_health_state(
        self: CbfObsDevice, health_state: HealthState
    ) -> None:
        """
        Callback for updating device's healthState attr.

        :param health_state: A HealthState enum representing the device's
        current health.
        """
        self.logger.info(
            "Updating device healthState but skipping pushing events..."
        )
        self._health_state = health_state
        # self.push_change_event("healthState", self._health_state)
        # self.push_archive_event("healthState", self._health_state)

    # ---------------
    # General methods
    # ---------------

    def _init_state_model(self: CbfObsDevice) -> None:
        """Set up the state model for the device."""
        super()._init_state_model()

        # CbfObsDevice uses the reduced observing state machine defined above
        self.obs_state_model = ObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
            state_machine_factory=CbfSubElementObsStateMachine,
        )

    def init_command_objects(self: CbfObsDevice) -> None:
        """Set up the command objects."""
        super().init_command_objects()

        for command_name, method_name in [
            ("ConfigureScan", "configure_scan"),
            ("Scan", "scan"),
            ("EndScan", "end_scan"),
            ("GoToIdle", "go_to_idle"),
            ("Abort", "abort"),
            ("ObsReset", "obs_reset"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name=command_name,
                    command_tracker=self._command_tracker,
                    component_manager=self.component_manager,
                    method_name=method_name,
                    logger=self.logger,
                ),
            )

    # --------
    # Commands
    # --------

    class InitCommand(SKAObsDevice.InitCommand):
        # pylint: disable=protected-access  # command classes are friend classes
        """A class for the CbfObsDevice's init_device() "command"."""

        def do(
            self: CbfObsDevice.InitCommand,
            *args: Any,
            **kwargs: Any,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :param args: positional arguments to this do method
            :param kwargs: keyword arguments to this do method

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            (result_code, msg) = super().do(*args, **kwargs)

            # Set initial simulation mode to True
            self._device._simulation_mode = SimulationMode.TRUE

            self._device._obs_state = ObsState.IDLE
            self._device._commanded_obs_state = ObsState.IDLE

            # JSON string, deliberately left in Tango layer
            self._device._last_scan_configuration = ""

            return (result_code, msg)

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def ConfigureScan(
        self: CbfObsDevice, argin: str
    ) -> DevVarLongStringArrayType:
        """
        Configure the observing device parameters for the current scan.

        :param argin: JSON formatted string with the scan configuration.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("ConfigureScan")
        result_code, command_id = command_handler(argin)
        # store configuration in Tango layer
        self._last_scan_configuration = argin
        return [[result_code], [command_id]]

    @command(
        dtype_in="uint64",
        doc_in="A string with the scan ID",
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def Scan(self: CbfObsDevice, argin: int) -> DevVarLongStringArrayType:
        """
        Start an observing scan.

        :param argin: Scan ID integer

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("Scan")
        result_code, command_id = command_handler(argin)
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def EndScan(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        End a running scan.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("EndScan")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def GoToIdle(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Transit the device from READY to IDLE obsState.
        To keep in line with LMC, using "GoToIdle" rather than the SKA base class
        equivalent "End".

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        # reset configuration in Tango layer
        self._last_scan_configuration = ""
        command_handler = self.get_command_object("GoToIdle")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def ObsReset(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Reset the observing device from a FAULT/ABORTED obsState to IDLE.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("ObsReset")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out=(
            "A tuple containing a return code and a string message "
            "indicating status. The message is for information purpose "
            "only."
        ),
    )
    @DebugIt()
    def Abort(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Abort the current observing process and move to ABORTED obsState.

        :return: A tuple containing a return code and a string message
            indicating status. The message is for information purpose
            only.
        """
        command_handler = self.get_command_object("Abort")
        result_code, command_id = command_handler()
        return [[result_code], [command_id]]

    # ----------------------
    # Unimplemented Commands
    # ----------------------

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def On(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Turn device on.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["On command rejected, as it is unimplemented for this device."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Off(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Turn device off.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["Off command rejected, as it is unimplemented for this device."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Standby(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Put the device into standby mode; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            [
                "Standby command rejected; Mid.CBF does not currently implement standby state."
            ],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Reset(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Reset the device; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            [
                "Reset command rejected, as it is unimplemented for this device."
            ],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def End(self: CbfObsDevice) -> DevVarLongStringArrayType:
        """
        Set obs device from READY to IDLE; currently unimplemented in Mid.CBF,
        as this is accomplished by GoToIdle.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["End command rejected; did you mean GoToIdle?"],
        )


# ----------
# Run server
# ----------


def main(*args: str, **kwargs: str) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    """
    return cast(int, CbfObsDevice.run_server(args=args or None, **kwargs))


if __name__ == "__main__":
    main()
