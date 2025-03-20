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

from threading import Event
from typing import Callable, Optional

from ska_control_model import (
    AdminMode,
    CommunicationStatus,
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
from ska_tango_base.base.test_mode_overrides import (
    TestModeOverrideMixin,
    overridable,
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

    # -------------
    # Communication
    # -------------

    # TODO
    def start_communicating(self: FHSSimCM, *args, **kwargs) -> None:
        self.logger.info("Entering FHSSimCM.start_communicating")
        self._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )
        self._update_component_state(power=PowerState.ON)

    def stop_communicating(self: FHSSimCM, *args, **kwargs) -> None:
        self.logger.info("Entering FHSSimCM.stop_communicating")
        self._update_component_state(power=PowerState.UNKNOWN)
        self._update_communication_state(
            communication_state=CommunicationStatus.DISABLED
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

        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=(
                    ResultCode.ABORTED,
                    f"{command_name} command aborted by task executor abort event.",
                ),
            )
            return

        task_callback(
            result=(
                ResultCode.OK,
                f"{command_name} completed OK",
            ),
            status=TaskStatus.COMPLETED,
        )
        self.logger.info(f"{command_name} end")
        return

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


class FHSSimBase(SKABaseDevice, TestModeOverrideMixin):
    """
    A generic base device simulator for Mid.CBF.
    Includes TestModeOverrideMixin to override certain key values.
    """

    # ----------
    # Properties
    # ----------

    DeviceID = device_property(dtype="uint16", default_value=0)

    # ----------
    # Attributes
    # ----------

    @attribute(dtype=TestMode, memorized=True, hw_memorized=True)
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

    @testMode.write  # type: ignore[no-redef]
    # pylint: disable=invalid-name
    def testMode(self: FHSSimBase, value: TestMode) -> None:
        """
        Set the Test Mode of the device.

        Override of TestModeOverrideMixin testMode.write so that testMode cannot
        be set to TestMode.NONE

        :param value: Test Mode
        """
        self.logger.warning("FHSSimBase testMode.write does nothing!")

    # --------------
    # Initialization
    # --------------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the FHSSimBase device's Init() command.
        """

        def do(
            self: FHSSimBase.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string message indicating status.
                     The message is for information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            # Default to TestMode.TEST
            self._device._test_mode = TestMode.TEST

            return (result_code, msg)

    def init_mixin(self: FHSSimBase) -> None:
        """
        Init enum attributes for converting to change event values.
        """
        super().init_mixin()
        self._test_mode_enum_attrs.update(
            {
                "adminMode": AdminMode,
                "state": DevState,
            }
        )

    def init_command_objects(self: FHSSimBase) -> None:
        """
        Register command objects (handlers) for this device's commands.

        Overrides SKABaseDevice method, keeping the base device commands Abort,
        CheckLongRunningCommandStatus and DebugDevice and registering any commands
        to be simulated as either a SimFastCommand or a SubmittedSlowCommand with the
        FHSSimCM.sim_command method as its target.
        """
        self._command_objects: dict[
            str, FastCommand[any] | SlowCommand[any]
        ] = {}

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

        # Simulated LRCs
        # None atm

        # Simulated fast commands
        # self.register_command_object(
        #     "SimFastCommand",
        #     self.SimFastCommand(
        #         command_name="SimFastCommand",
        #         component_manager=self.component_manager,
        #         logger=self.logger,
        #     ),
        # )

    def create_component_manager(self: FHSSimBase) -> FHSSimCM:
        return FHSSimCM(
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    # ---------------------
    # Long Running Commands
    # ---------------------

    # None atm

    # -------------
    # Fast Commands
    # -------------

    class SimFastCommand(FastCommand):
        """
        A command to test the mesh of SLIM Links.
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
            Determine if SlimTest command is allowed.

            :return: True if command is allowed, otherwise False
            """
            return self.component_manager.command_allowed

        def do(self: FHSSimBase.SimFastCommand) -> tuple[ResultCode, str]:
            """
            SLIM Test Command. Checks the BER and health status of the mesh's configured links.

            :return: A tuple containing a return code and a string
                message containing a report on the health of the Mesh or error message
                if exception is caught.
            :rtype: (ResultCode, str)
            """
            if self.is_allowed():
                pass
            return (ResultCode.REJECTED, f"{self.command_name} not allowed")

    # @command(
    #     dtype_out="DevVarLongStringArray",
    #     doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    # )
    # @DebugIt()
    # def SimFastCommand(self: FHSSimBase) -> DevVarLongStringArrayType:
    #     handler = self.get_command_object("SimFastCommand")
    #     return_code, message = handler()
    #     return [[return_code], [message]]


class FHSSimVCC(FHSSimBase):
    # -----------------
    # Device Properties
    # -----------------

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
    @overridable
    def obsState(self: FHSSimVCC) -> ObsState:
        """
        Read the Observation State of the device.

        :return: the current ObsState enum value
        """
        return self._obs_state

    @attribute(dtype="uint16", doc="The observing device ID.")
    @overridable
    def deviceID(self: FHSSimVCC) -> int:
        """
        Read the device's ID.

        :return: the current DeviceID value
        """
        return self.DeviceID

    @attribute(
        dtype="uint64",
        doc="The scan identification number to be inserted in the output products.",
    )
    @overridable
    def scanID(self: FHSSimVCC) -> int:
        """
        Read the current scan ID of the device.

        :return: the current scan_id value
        """
        return self._scan_id

    @attribute(
        dtype="str",
        doc="The configuration ID specified into the JSON configuration.",
    )
    @overridable
    def configurationID(self: FHSSimVCC) -> str:
        """
        Read the current configuration ID of the device.

        :return: the current config_id value
        """
        return self._config_id

    @attribute(dtype="str", doc="The last valid scan configuration.")
    @overridable
    def lastScanConfiguration(self: FHSSimVCC) -> str:
        """
        Read the last valid scan configuration of the device.

        :return: the current _last_scan_configuration value
        """
        return self._last_scan_configuration

    @attribute(dtype=SimulationMode, memorized=True, hw_memorized=True)
    @overridable
    def simulationMode(self: FHSSimVCC) -> SimulationMode:
        """
        Read the Simulation Mode of the device.

        :return: Simulation Mode of the device.
        """
        return self._simulation_mode

    @simulationMode.write
    def simulationMode(self: FHSSimVCC, value: SimulationMode) -> None:
        """
        Set the simulation mode of the device.

        :param value: SimulationMode
        """
        self.logger.debug(f"Writing simulationMode to {value}")
        self._simulation_mode = value

    @attribute(
        dtype="str",
        memorized=True,
        hw_memorized=True,
        doc="VCC's associated DISH ID",
    )
    @overridable
    def dishID(self: FHSSimVCC) -> str:
        """
        Read the dishID attribute.

        :return: the Vcc's DISH ID.
        :rtype: str
        """
        return self._dish_id

    @dishID.write
    def dishID(self: FHSSimVCC, value: str) -> None:
        """
        Write the dishID attribute.

        :param value: the dishID value.
        """
        self.logger.info(f"Writing dishID to {value}")
        if self._dish_id != value:
            self._dish_id = value
            self.push_change_event("dishID", value)
            self.push_archive_event("dishID", value)

    @attribute(
        abs_change=1,
        dtype="uint16",
        memorized=True,
        hw_memorized=True,
        doc="Subarray membership",
    )
    @overridable
    def subarrayMembership(self: FHSSimVCC) -> int:
        """
        Read the subarrayMembership attribute.

        :return: the subarray membership (0 = no affiliation).
        :rtype: int
        """
        return self._subarray_membership

    @subarrayMembership.write
    def subarrayMembership(self: FHSSimVCC, value: int) -> None:
        """
        Write the subarrayMembership attribute.

        :param value: the subarray membership value (0 = no affiliation).
        """
        self.logger.info(f"Writing subarrayMembership to {value}")
        if self._subarray_membership != value:
            self._subarray_membership = value
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
    @overridable
    def frequencyBand(self: FHSSimVCC) -> DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band (being observed by the current scan, one of
            ["1", "2", "3", "4", "5a", "5b"]).
        :rtype: tango.DevEnum
        """
        return self._frequency_band

    @attribute(
        dtype="str", doc="The last valid scan configuration sent to HPS."
    )
    @overridable
    def lastHpsScanConfiguration(self: FHSSimVCC) -> str:
        """
        Read the last valid scan configuration of the device sent to HPS.

        :return: the current last_hps_scan_configuration value
        """
        return self._last_hps_scan_configuration

    # --------------
    # Initialization
    # --------------

    class InitCommand(FHSSimBase.InitCommand):
        """
        A class for the FHSSimVCC's init_device() "command".
        """

        def do(
            self: FHSSimVCC.InitCommand,
            *args: any,
            **kwargs: any,
        ) -> DevVarLongStringArrayType:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            :rtype: (ResultCode, str)
            """
            (result_code, msg) = super().do(*args, **kwargs)

            # initialize attribute values
            self._device._simulation_mode = SimulationMode.TRUE
            self._device._obs_state = ObsState.IDLE
            self._device._last_scan_configuration = ""
            self._device._scan_id = 0
            self._device._config_id = ""
            self._device._dish_id = ""
            self._device._frequency_band = 0
            self._device._subarray_membership = 0
            self._device._last_hps_scan_configuration = ""

            for attr_name in [
                "obsState",
                "dishID",
                "frequencyBand",
                "subarrayMembership",
            ]:
                self._device.set_change_event(attr_name, True)
                self._device.set_archive_event(attr_name, True)

            return (result_code, msg)

    def init_mixin(self: FHSSimBase) -> None:
        """
        Init enum attributes for converting to change event values.
        """
        super().init_mixin()
        self._test_mode_enum_attrs.update(
            {
                "obsState": ObsState,
            }
        )

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

    def _update_obs_state(self: FHSSimVCC, obs_state: ObsState) -> None:
        """
        Perform Tango operations in response to a change in obsState.

        This helper method is passed to the observation state model as a
        callback, so that the model can trigger actions in the Tango
        device.

        :param obs_state: the new obs_state value
        """
        self._obs_state = obs_state
        self.push_change_event("obsState", obs_state)
        self.push_archive_event("obsState", obs_state)

    # -------------
    # Fast Commands
    # -------------

    # None atm

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
        self: FHSSimBase, argin: str
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
        self: FHSSimBase, argin: str
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
    def Scan(self: FHSSimBase, argin: int) -> DevVarLongStringArrayType:
        handler = self.get_command_object("Scan")
        return_code, message = handler("Scan")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def EndScan(self: FHSSimBase) -> DevVarLongStringArrayType:
        handler = self.get_command_object("EndScan")
        return_code, message = handler("EndScan")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def GoToIdle(self: FHSSimBase) -> DevVarLongStringArrayType:
        handler = self.get_command_object("GoToIdle")
        return_code, message = handler("GoToIdle")
        return [[return_code], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
        doc_out="Tuple containing a return code and a string message indicating the status of the command.",
    )
    @DebugIt()
    def ObsReset(self: FHSSimBase) -> DevVarLongStringArrayType:
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
