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
Device simulators for Mid.CBF MCS
"""

from __future__ import annotations

import tango
import threading
from typing import Optional
import logging

from ska_tango_base.base.base_component_manager import BaseComponentManager, TaskCallbackType
from ska_tango_base.base.base_device import SKABaseDevice, DevVarLongStringArrayType
from ska_control_model import AdminMode, CommunicationStatus, ObsState, ObsStateModel, PowerState, ResultCode, SimulationMode, TaskStatus
from tango.server import attribute, command, device_property
from .obs_state_machine import FhsObsStateModel

__all__ = ["VCCSimCM", "VCCSimDevice"]

class DummyCM:
    """
    A dummy component manager for FHS simulators.
    Simply contains overrides for any SKABaseDevice calls to component managers.
    """
    def __init__(self: DummyCM, logger: logging.Logger):
        self.logger = logger
        self.max_queued_tasks = 0
        self.max_executing_tasks = 1

    def start_communicating(self: DummyCM):
        self.logger.info("start_communicating")

    def stop_communicating(self: DummyCM):
        self.logger.info("stop_communicating")

class FHSSimulator(SKABaseDevice):
    """
    A generic FHS device simulator for Mid.CBF.
    """
    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the simulator's init_device() "command".
        """

        def do(
            self: FHSSimulator.InitCommand,
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

            # Initialize attribute values
            self._device._communication_state_lock = threading.Lock()
            self._device._communication_state = CommunicationStatus.DISABLED

            self._device._component_state_lock = threading.Lock()
            self._device._component_state = {
                "fault": False,
                "power": PowerState.UNKNOWN,
            }

            # TODO: set additional change/archive events

            return (result_code, msg)

    def create_component_manager(self: FHSSimulator) -> DummyCM:
        return DummyCM(logger=self.logger)
    
    def init_command_objects(self: FHSSimulator):
        self.logger.info("init_command_objects")
        # TODO

    def _update_communication_state(self: FHSSimulator, communication_state: CommunicationStatus):
        """
        Handle a change in communication status.

        This is a helper method for use by subclasses.

        :param communication_state: the new communication status of the
            component manager.
        """
        with self._communication_state_lock:
            if self._communication_state != communication_state:
                self._communication_state = communication_state
                super()._communication_state_changed(communication_state)

    def _update_component_state(
        self: FHSSimulator,
        **kwargs: any,
    ) -> None:
        """
        Handle a change in component state.

        This is a helper method for use by subclasses.

        :param kwargs: key/values for state
        """
        callback_kwargs = {}

        with self._component_state_lock:
            for key, value in kwargs.items():
                if self._component_state[key] != value:
                    self._component_state[key] = value
                    callback_kwargs[key] = value
            if callback_kwargs:
                self._component_state_changed(**callback_kwargs)

class FHSObsSimulator(FHSSimulator):
    """
    A generic FHS Obs device simulator for Mid.CBF.
    """

    class InitCommand(FHSSimulator.InitCommand):
        """
        A class for the simulator's init_device() "command".
        """

        def do(
            self: FHSObsSimulator.InitCommand,
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

            # Initialize attribute values
            self._device._component_state.update(
                {
                    "configured": False,
                    "scanning": False,
                    "obsfault": False,
                }
            )

            self._device._obs_state = ObsState.IDLE

            # TODO: set additional change/archive events
            self._device.set_change_event("obsState", True)
            self._device.set_archive_event("obsState", True)

            return (result_code, msg)

    def _update_obs_state(
        self: FHSObsSimulator, obs_state: ObsState
    ) -> None:
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

    def _init_state_model(self: FHSObsSimulator) -> None:
        """Set up the state model for the device."""
        super()._init_state_model()

        # CbfObsDevice uses the reduced observing state machine defined above
        self.obs_state_model = FhsObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
        )

    def _component_state_changed(
        self: FHSObsSimulator,
        fault: Optional[bool] = None,
        power: Optional[PowerState] = None,
        configured: Optional[bool] = None,
        scanning: Optional[bool] = None,
        obsfault: Optional[bool] = None,
    ) -> None:
        super()._component_state_changed(fault=fault, power=power)

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

    # ----------
    # Attributes
    # ----------

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=ObsState
    )
    def obsState(self: FHSObsSimulator) -> ObsState:
        """
        Read the Observation State of the device.

        :return: the current ObsState enum value
        """
        return self._obs_state
