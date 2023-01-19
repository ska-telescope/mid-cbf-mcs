# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.
#
# """
# HPS DS FSP Corr Controller Simulator Class
#
# This class is used to simulate the behaviour of the HPS FSP Corr Controller
# devices when the Talon-DX hardware is not connected.
#

from __future__ import annotations  # allow forward references in type hints

import tango

__all__ = ["HpsFspCorrControllerSimulator"]


class HpsFspCorrControllerSimulator:
    """
    HpsFspCorrControllerSimulator class used to simulate the behaviour of
    the HPS FSP Corr Controller devices
    when the Talon-DX hardware is not connected.

    :param device_name: Identifier for the device instance
    """

    def __init__(
        self: HpsFspCorrControllerSimulator, device_name: str
    ) -> None:
        self.device_name = device_name

        self._state = tango.DevState.INIT

        self._fsp_id = ""
        self._fspUnitID = 0
        self._fqdn = ""
        self._scan_id = "0"

    # Properties that match the Tango attributes in the band devices
    @property
    def fspID(self) -> str:
        """Return the Fsp ID attribute."""
        return self._fsp_id

    @property
    def fspUnitID(self) -> int:
        """Return the Fsp Unit ID attribute."""
        return self._fsp_unit_id

    @property
    def fqdn(self) -> str:
        """Return the fqdn attribute."""
        return self._fqdn

    # Methods that match the Tango commands in the band devices
    def State(self: HpsFspCorrControllerSimulator) -> tango.DevState:
        """Get the current state of the device"""
        return self._state

    def init_device(
        self: HpsFspCorrControllerSimulator, json_str: str
    ) -> None:
        """
        Initialize the common/constant parameters of this FSP device.

        :param json_str: JSON-formatted string containing the parameters
        """
        pass

    def ConfigureScan(
        self: HpsFspCorrControllerSimulator, json_str: str
    ) -> None:
        """
        Execute a configure scan operation.

        :param json_str: JSON-formatted string containing the scan configuration
                         parameters
        """
        pass

    def Scan(self: HpsFspCorrControllerSimulator, scan_id: str) -> None:
        """
        Execute a scan operation.

        :param scan_id: Scan identifier
        """
        self._scan_id = scan_id

    def EndScan(self: HpsFspCorrControllerSimulator) -> None:
        """End the scan."""
        self._scan_id = "0"

    def Abort(self: HpsFspCorrControllerSimulator) -> None:
        """Abort whatever action is currently executing."""
        pass

    def GoToIdle(self: HpsFspCorrControllerSimulator) -> None:
        """Set the device state to IDLE"""
        pass

    def UpdateDelayModels(
        self: HpsFspCorrControllerSimulator, delay_model: str
    ) -> None:
        """
        Execute an update delay model operation.

        :param delay_model: Delay Model
        """
        pass
