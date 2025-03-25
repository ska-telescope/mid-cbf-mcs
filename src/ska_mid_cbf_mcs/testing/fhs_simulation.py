# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2025 National Research Council of Canada

"""
FHSSimBase

Generic simulated Tango device for Mid.CBF
"""

from __future__ import annotations

import json
from threading import Event
from typing import Callable, Optional

from pydantic.v1.utils import deep_update
from ska_control_model import (
    AdminMode,
    CommunicationStatus,
    ControlMode,
    HealthState,
    LoggingLevel,
    ObsState,
    ObsStateModel,
    PowerState,
    ResultCode,
    SimulationMode,
    TaskStatus,
    TestMode,
)
from ska_tango_base.base.base_device import (
    DevVarLongStringArrayType,
    SKABaseDevice,
)
from ska_tango_base.commands import (
    FastCommand,
    SlowCommand,
    SubmittedSlowCommand,
)
from ska_tango_base.executor.executor_component_manager import (
    TaskExecutorComponentManager,
)
from tango import DebugIt, DevEnum, DevState
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.obs_device import CbfSubElementObsStateMachine

__all__ = ["FHSSimCM", "FHSSimBase", "main"]


class FHSSimCM(TaskExecutorComponentManager):
    """
    A simulated component manager for FHS simulator devices.
    """

    command_allowed: bool
    command_overrides: dict[str, any]

    def __init__(
        self: FHSSimCM,
        *args: any,
        **kwargs: any,
    ) -> None:
        """
        Initialise a new FHSSimCM instance.
        """

        # supply operating state machine trigger keywords
        super().__init__(
            *args,
            invoked_action=None,
            completed_action=None,
            fault=None,
            power=None,
            configured=None,
            scanning=None,
            resourced=None,
            obsfault=None,
            **kwargs,
        )

        # TODO: Set by device to trigger "command not allowed" type failures
        self.command_allowed = True
        self.command_overrides = {}

    # -------------
    # Communication
    # -------------

    # TODO
    def start_communicating(self: FHSSimCM, *args, **kwargs) -> None:
        self.logger.info("Entering FHSSimCM.start_communicating")

        communication_state = self.command_overrides[
            "start_communicating"
        ].get("communication_state", None)
        if communication_state is not None:
            self._update_communication_state(
                communication_state=CommunicationStatus[communication_state]
            )

        power_state = self.command_overrides["start_communicating"].get(
            "power_state", None
        )
        if power_state is not None:
            self._update_component_state(power=PowerState[power_state])

    def stop_communicating(self: FHSSimCM, *args, **kwargs) -> None:
        self.logger.info("Entering FHSSimCM.stop_communicating")

        power_state = self.command_overrides["stop_communicating"].get(
            "power_state", None
        )
        if power_state is not None:
            self._update_component_state(power=PowerState[power_state])

        communication_state = self.command_overrides["stop_communicating"].get(
            "communication_state", None
        )
        if communication_state is not None:
            self._update_communication_state(
                communication_state=CommunicationStatus[communication_state]
            )

    # --------
    # Commands
    # --------

    def is_sim_command_allowed(self: FHSSimCM) -> bool:
        """
        Check if the On command is allowed.

        :return: True if the On command is allowed, else False.
        """

        return self.command_allowed

    def _sim_command(
        self: FHSSimCM,
        command_name: str,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        self.logger.info(f"{command_name} begin")

        invoked_action = self.command_overrides[command_name].get(
            "invoked_action", None
        )
        if invoked_action is not None:
            self._update_component_state(invoked_action=invoked_action)

        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    f"{command_name} command aborted by task executor abort event.",
                ),
            )
            return

        component_state = self.command_overrides[command_name].get(
            "component_state", None
        )
        if component_state is not None:
            self._update_component_state(**component_state)

        task_callback(
            result=(
                ResultCode[
                    self.command_overrides[command_name]["result_code"]
                ],
                self.command_overrides[command_name]["message"],
            ),
            status=TaskStatus.COMPLETED,
        )

        completed_action = self.command_overrides[command_name].get(
            "completed_action", None
        )
        if completed_action is not None:
            self._update_component_state(completed_action=completed_action)

        self.logger.info(f"{command_name} end")

    def sim_command(
        self: FHSSimCM,
        command_name: str,
        task_callback: Optional[Callable] = None,
    ) -> tuple[ResultCode, str]:
        """
        Submit simulated command operation method to task executor queue.

        :param command_name: name of the command to be simulated
        :param task_callback: Callback function to update task status
        :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
        :rtype: (ResultCode, str)
        """
        return self.submit_task(
            self._sim_command,
            is_cmd_allowed=self.is_sim_command_allowed,
            args=[command_name],
            task_callback=task_callback,
        )


class FHSSimBase(SKABaseDevice):
    """
    A generic base device simulator for Mid.CBF.
    Includes TestModeOverrideMixin to override certain key values.
    """

    # --------------
    # Initialization
    # --------------

    _test_mode: TestMode
    _test_overrides: dict[str, any]
    _enum_attrs: dict[str, any]
    _command_objects: dict[str, FastCommand[any] | SlowCommand[any]]

    _attribute_overrides: dict[str, any] = {}
    _command_overrides: dict[str, any] = {}

    def init_overrides(self: FHSSimBase) -> None:
        """Add our variables to the class we are extending."""
        self._test_mode = TestMode.TEST
        self._test_overrides = {}
        self._enum_attrs = {
            "adminMode": AdminMode,
            "controlMode": ControlMode,
            "healthState": HealthState,
            "loggingLevel": LoggingLevel,
            "state": DevState,
            "simulationMode": SimulationMode,
            "testMode": TestMode,
        }

    def init_command_objects(self: FHSSimBase) -> None:
        """
        Register command objects (handlers) for this device's commands.

        Overrides SKABaseDevice method, keeping the base device commands Abort,
        CheckLongRunningCommandStatus and DebugDevice and registering any commands
        to be simulated as either a SimFastCommand or a SubmittedSlowCommand with the
        FHSSimCM.sim_command method as its target.
        """
        self.init_overrides()

        self._command_objects = {}

        # Base class required commands
        self.register_command_object(
            "Abort",
            self.AbortCommand(
                self._command_tracker,
                self.component_manager,
                None,
                self.logger,
            ),
        )
        self.register_command_object(
            "CheckLongRunningCommandStatus",
            self.CheckLongRunningCommandStatusCommand(
                self._command_tracker, self.logger
            ),
        )
        self.register_command_object(
            "DebugDevice",
            self.DebugDeviceCommand(self, logger=self.logger),
        )

    def create_component_manager(self: FHSSimBase) -> FHSSimCM:
        return FHSSimCM(
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    # ----------
    # Properties
    # ----------

    DeviceID = device_property(dtype="uint16", default_value=0)

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=TestMode)
    # pylint: disable=invalid-name
    def testMode(
        self: FHSSimBase,
    ) -> TestMode:
        """
        Read the Test Mode of the device.

        Either no test mode or an indication of the test mode.

        :return: Test Mode of the device
        """
        return self._test_mode

    @attribute(
        dtype=str,
        doc="Attribute value overrides (JSON dict)",
    )  # type: ignore[misc]
    def test_overrides(self: FHSSimBase) -> str:
        """
        Read the current override configuration.

        :return: JSON-encoded dictionary
        """
        return json.dumps(self._test_overrides)

    @test_overrides.write  # type: ignore[no-redef, misc]
    def test_overrides(self: FHSSimBase, value_str: str) -> None:
        """
        Write new override configuration.
        Example dict of overrides:
        {
            "attributes": {
                "integerAttribute": 0,
                "stringAttribute": "test",
                "healthState": "OK",
            },
            "commands": {
                "On": {
                    "result_code": "OK",
                    "message": "On completed OK",
                },
                "ConfigureScan": {
                    "result_code": "FAILED",
                    "message": "ConfigureScan command failed",
                },
            }
        }

        :param value_str: JSON-encoded dict of overrides
        """
        try:
            value_dict = json.loads(value_str)
        except json.JSONDecodeError as je:
            self.logger.error(f"{je}")

        self._test_overrides = value_dict

        if "commands" in value_dict:
            self._command_overrides = deep_update(
                self._command_overrides, value_dict["commands"]
            )
            self.component_manager.command_overrides.update(
                value_dict["commands"]
            )
        else:
            self.logger.info("No command overrides provided")

        # Send events for all attribute overrides
        if "attributes" in value_dict:
            for attr_name, value in value_dict["attributes"].items():
                # Only push event if attribute value has changed
                if self._attribute_overrides[attr_name] == value:
                    continue

                self._attribute_overrides[attr_name] = value

                # Convert to enum value if enum attribute
                if attr_name in self._enum_attrs and isinstance(value, str):
                    value = self._enum_attrs[attr_name][value]

                attr_cfg = self.get_device_attr().get_attr_by_name(attr_name)
                if attr_cfg.is_change_event():
                    self.push_change_event(attr_name, value)
                if attr_cfg.is_archive_event():
                    self.push_archive_event(attr_name, value)
        else:
            self.logger.info("No attribute overrides provided")

    # ---------------------
    # Long Running Commands
    # ---------------------

    # None atm

    # -------------
    # Fast Commands
    # -------------

    class SimFastCommand(FastCommand):
        """
        An object to simulate FastCommand behaviour.
        """

        def __init__(
            self: FHSSimBase.SimFastCommand,
            *args,
            command_name: str,
            component_manager: TaskExecutorComponentManager,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.command_name = command_name
            self.component_manager = component_manager

        def is_allowed(self: FHSSimBase.SimFastCommand) -> bool:
            """
            Determine if command is allowed.

            :return: True if command is allowed, otherwise False
            """
            return self.component_manager.command_allowed

        def do(self: FHSSimBase.SimFastCommand) -> tuple[ResultCode, str]:
            """
            Perform the user-specified functionality of the command.

            :return: A tuple containing a return code and a string
                message containing a report on the health of the Mesh or error message
                if exception is caught.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                result_code = self.component_manager.command_overrides[
                    self.command_name
                ]["result_code"]
                message = self.component_manager.command_overrides[
                    self.command_name
                ]["message"]
                return (ResultCode[result_code], message)
            return (ResultCode.REJECTED, f"{self.command_name} not allowed")


class FHSSimVCC(FHSSimBase):
    # --------------
    # Initialization
    # --------------

    def init_overrides(self: FHSSimVCC) -> None:
        """
        Init enum attributes for converting to change event values.
        """
        super().init_overrides()

        self._attribute_overrides.update(
            {
                "obsState": "IDLE",
                "dishID": "",
                "frequencyBand": 0,
                "subarrayMembership": 0,
            }
        )

        self._command_overrides.update(
            {
                "start_communicating": {
                    "communication_state": "ESTABLISHED",
                    "power_state": "ON",
                },
                "stop_communicating": {
                    "communication_state": "DISABLED",
                    "power_state": "UNKNOWN",
                },
                "ConfigureBand": {
                    "result_code": "OK",
                    "message": "ConfigureBand completed OK",
                },
                "ConfigureScan": {
                    "result_code": "OK",
                    "message": "ConfigureScan completed OK",
                    "invoked_action": "configure_invoked",
                    "completed_action": "configure_completed",
                    "component_state": {
                        "configured": True,
                    },
                },
                "Scan": {
                    "result_code": "OK",
                    "message": "Scan completed OK",
                    "component_state": {
                        "scanning": True,
                    },
                },
                "EndScan": {
                    "result_code": "OK",
                    "message": "EndScan completed OK",
                    "component_state": {
                        "scanning": False,
                    },
                },
                "GoToIdle": {
                    "result_code": "OK",
                    "message": "GoToIdle completed OK",
                    "component_state": {
                        "configured": False,
                    },
                },
                "ObsReset": {
                    "result_code": "OK",
                    "message": "ObsReset completed OK",
                    "invoked_action": "obsreset_invoked",
                    "completed_action": "obsreset_completed",
                    "component_state": {
                        "configured": False,
                        "obsfault": False,
                    },
                },
            }
        )
        self.component_manager.command_overrides.update(
            self._command_overrides
        )

        self._enum_attrs.update(
            {
                "obsState": ObsState,
            }
        )

        # initialize change events
        for attr_name in [
            "obsState",
            "dishID",
            "frequencyBand",
            "subarrayMembership",
        ]:
            self.set_change_event(attr_name, True)
            self.set_archive_event(attr_name, True)

    def init_command_objects(self: FHSSimVCC) -> None:
        """
        Register command objects (handlers) for this device's commands.

        Registers any commands to be simulated as either a SimFastCommand or a
        SubmittedSlowCommand with the FHSSimCM.sim_command method as its target.
        """
        super().init_command_objects()

        # Simulated LRCs
        for command_name in [
            "ConfigureBand",
            "ConfigureScan",
            "Scan",
            "EndScan",
            "GoToIdle",
            "ObsReset",
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name=command_name,
                    command_tracker=self._command_tracker,
                    component_manager=self.component_manager,
                    method_name="sim_command",
                    logger=self.logger,
                ),
            )

        # Simulated fast commands
        # self.register_command_object(
        #     "On",
        #     self.SimFastCommand(
        #         command_name="On",
        #         component_manager=self.component_manager,
        #         logger=self.logger,
        #     ),
        # )

    # TODO
    def _init_state_model(self: FHSSimVCC) -> None:
        """Set up the state model for the device."""
        super()._init_state_model()

        # CbfObsDevice uses the reduced observing state machine defined above
        self.obs_state_model = ObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
            state_machine_factory=CbfSubElementObsStateMachine,
        )

    # ----------
    # Callbacks
    # ----------

    def _component_state_changed(
        self: FHSSimVCC,
        invoked_action: Optional[str] = None,
        completed_action: Optional[str] = None,
        fault: Optional[bool] = None,
        power: Optional[PowerState] = None,
        resourced: Optional[bool] = None,
        configured: Optional[bool] = None,
        scanning: Optional[bool] = None,
        obsfault: Optional[bool] = None,
    ) -> None:
        args = {
            "invoked_action": invoked_action,
            "completed_action": completed_action,
            "fault": fault,
            "power": power,
            "resourced": resourced,
            "configured": configured,
            "scanning": scanning,
            "obsfault": obsfault,
        }
        self.logger.info(f"_component_state_changed args: {args}")

        if invoked_action is not None:
            self.obs_state_model.perform_action(invoked_action)
        if completed_action is not None:
            self.obs_state_model.perform_action(completed_action)

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

    def _update_obs_state(self: FHSSimVCC, obs_state: ObsState) -> None:
        """
        Perform Tango operations in response to a change in obsState.

        This helper method is passed to the observation state model as a
        callback, so that the model can trigger actions in the Tango
        device.

        :param obs_state: the new obs_state value
        """
        self._attribute_overrides["obsState"] = obs_state
        self.push_change_event("obsState", obs_state)
        self.push_archive_event("obsState", obs_state)

    # ----------
    # Properties
    # ----------

    TalonLRUAddress = device_property(dtype="str")

    VccControllerAddress = device_property(dtype="str")

    Band1And2Address = device_property(dtype="str")

    Band3Address = device_property(dtype="str")

    Band4Address = device_property(dtype="str")

    Band5Address = device_property(dtype="str")

    LRCTimeout = device_property(dtype=("str"))

    # ----------
    # Attributes
    # ----------

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=ObsState
    )
    def obsState(self: FHSSimVCC) -> ObsState:
        """
        Read the Observation State of the device.

        :return: the current ObsState enum value
        """
        return ObsState[self._attribute_overrides.get("obsState", "IDLE")]

    @attribute(
        dtype="str",
        memorized=True,
        hw_memorized=True,
        doc="VCC's associated DISH ID",
    )
    def dishID(self: FHSSimVCC) -> str:
        """
        Read the dishID attribute.

        :return: the Vcc's DISH ID.
        :rtype: str
        """
        return self._attribute_overrides.get("dishID", "")

    @dishID.write
    def dishID(self: FHSSimVCC, value: str) -> None:
        """
        Write the dishID attribute.

        :param value: the dishID value.
        """
        self.logger.info(f"Writing dishID to {value}")
        if self._attribute_overrides["dishID"] != value:
            self._attribute_overrides["dishID"] = value
            self.push_change_event("dishID", value)
            self.push_archive_event("dishID", value)

    @attribute(
        abs_change=1,
        dtype="uint16",
        memorized=True,
        hw_memorized=True,
        doc="Subarray membership",
    )
    def subarrayMembership(self: FHSSimVCC) -> int:
        """
        Read the subarrayMembership attribute.

        :return: the subarray membership (0 = no affiliation).
        :rtype: int
        """
        return self._attribute_overrides.get("subarrayMembership", 0)

    @subarrayMembership.write
    def subarrayMembership(self: FHSSimVCC, value: int) -> None:
        """
        Write the subarrayMembership attribute.

        :param value: the subarray membership value (0 = no affiliation).
        """
        self.logger.info(f"Writing subarrayMembership to {value}")
        if self._attribute_overrides["subarrayMembership"] != value:
            self._attribute_overrides["subarrayMembership"] = value
            self.push_change_event("subarrayMembership", value)
            self.push_archive_event("subarrayMembership", value)

    @attribute(
        abs_change=1,
        dtype=DevEnum,
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
        doc=(
            "The frequency band observed by the current scan: "
            "an enum that can be one of ['1', '2', '3', '4', '5a', '5b']"
        ),
    )
    def frequencyBand(self: FHSSimVCC) -> DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band (being observed by the current scan, one of
            ["1", "2", "3", "4", "5a", "5b"]).
        :rtype: tango.DevEnum
        """
        return self._attribute_overrides.get("frequencyBand", 0)

    # -------------
    # Fast Commands
    # -------------

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    # )
    # @DebugIt()
    # def On(self: FHSSimBase) -> DevVarLongStringArrayType:
    #     handler = self.get_command_object("On")
    #     return_code, message = handler()
    #     return [[return_code], [message]]

    # ---------------------
    # Long Running Commands
    # ---------------------

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the VCC band configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConfigureBand(
        self: FHSSimVCC, argin: str
    ) -> DevVarLongStringArrayType:
        handler = self.get_command_object("ConfigureBand")
        return_code, message = handler("ConfigureBand")
        return [[return_code], [message]]

    @command(
        dtype_in="DevString",
        doc_in="JSON formatted string with the scan configuration.",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ConfigureScan(
        self: FHSSimVCC, argin: str
    ) -> DevVarLongStringArrayType:
        handler = self.get_command_object("ConfigureScan")
        return_code, message = handler("ConfigureScan")
        return [[return_code], [message]]

    @command(
        dtype_in="uint64",
        doc_in="scan ID integer",
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def Scan(self: FHSSimVCC, argin: int) -> DevVarLongStringArrayType:
        handler = self.get_command_object("Scan")
        return_code, message = handler("Scan")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def EndScan(self: FHSSimVCC) -> DevVarLongStringArrayType:
        handler = self.get_command_object("EndScan")
        return_code, message = handler("EndScan")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def GoToIdle(self: FHSSimVCC) -> DevVarLongStringArrayType:
        handler = self.get_command_object("GoToIdle")
        return_code, message = handler("GoToIdle")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ObsReset(self: FHSSimVCC) -> DevVarLongStringArrayType:
        handler = self.get_command_object("ObsReset")
        return_code, message = handler("ObsReset")
        return [[return_code], [message]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return FHSSimVCC.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
