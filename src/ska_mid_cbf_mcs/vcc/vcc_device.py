# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2019 National Research Council of Canada

from __future__ import annotations

# Tango imports
import tango
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import SubmittedSlowCommand
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.obs_device import CbfObsDevice
from ska_mid_cbf_mcs.vcc.vcc_component_manager import VccComponentManager

__all__ = ["Vcc", "main"]


class Vcc(CbfObsDevice):
    """
    Vcc TANGO device class for the prototype
    """

    # -----------------
    # Device Properties
    # -----------------

    TalonLRUAddress = device_property(dtype="str")

    VccControllerAddress = device_property(dtype="str")

    Band1And2Address = device_property(dtype="str")

    Band3Address = device_property(dtype="str")

    Band4Address = device_property(dtype="str")

    Band5Address = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype="str",
        memorized=True,
        hw_memorized=True,
        doc="VCC's associated DISH ID",
    )
    def dishID(self: Vcc) -> str:
        """
        Read the dishID attribute.

        :return: the Vcc's DISH ID.
        :rtype: str
        """
        return self.component_manager.dish_id

    @dishID.write
    def dishID(self: Vcc, value: str) -> None:
        """
        Write the dishID attribute.

        :param value: the dishID value.
        """
        self.logger.debug(f"Writing dishID to {value}")
        if self.component_manager.dish_id != value:
            self.component_manager.dish_id = value
            self.push_change_event("dishID", value)
            self.push_archive_event("dishID", value)

    @attribute(
        abs_change=1,
        dtype="uint16",
        memorized=True,
        hw_memorized=True,
        doc="Subarray membership",
    )
    def subarrayMembership(self: Vcc) -> int:
        """
        Read the subarrayMembership attribute.

        :return: the subarray membership (0 = no affiliation).
        :rtype: int
        """
        return self._subarray_membership

    @subarrayMembership.write
    def subarrayMembership(self: Vcc, value: int) -> None:
        """
        Write the subarrayMembership attribute.

        :param value: the subarray membership value (0 = no affiliation).
        """
        self.logger.debug(f"Writing subarrayMembership to {value}")
        if self._subarray_membership != value:
            self._subarray_membership = value
            self.push_change_event("subarrayMembership", value)
            self.push_archive_event("subarrayMembership", value)

    @attribute(
        abs_change=1,
        dtype=tango.DevEnum,
        enum_labels=["1", "2", "3", "4", "5a", "5b"],
        doc=(
            "The frequency band observed by the current scan: "
            "an enum that can be one of ['1', '2', '3', '4', '5a', '5b']"
        ),
    )
    def frequencyBand(self: Vcc) -> tango.DevEnum:
        """
        Read the frequencyBand attribute.

        :return: the frequency band (being observed by the current scan, one of
            ["1", "2", "3", "4", "5a", "5b"]).
        :rtype: tango.DevEnum
        """
        return self.component_manager.frequency_band

    @attribute(
        dtype="str", doc="The last valid scan configuration sent to HPS."
    )
    def lastHpsScanConfiguration(self: Vcc) -> str:
        """
        Read the last valid scan configuration of the device sent to HPS.

        :return: the current last_hps_scan_configuration value
        """
        return self.component_manager.last_hps_scan_configuration

    # --------------
    # Initialization
    # --------------

    def init_command_objects(self: Vcc) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        self.register_command_object(
            "ConfigureBand",
            SubmittedSlowCommand(
                command_name="ConfigureBand",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="configure_band",
                logger=self.logger,
            ),
        )

    def create_component_manager(self: Vcc) -> VccComponentManager:
        return VccComponentManager(
            talon_lru=self.TalonLRUAddress,
            vcc_controller=self.VccControllerAddress,
            vcc_band=[
                self.Band1And2Address,
                self.Band3Address,
                self.Band4Address,
                self.Band5Address,
            ],
            logger=self.logger,
            attr_change_callback=self.push_change_event,
            attr_archive_callback=self.push_archive_event,
            health_state_callback=self._update_health_state,
            communication_state_callback=self._communication_state_changed,
            obs_command_running_callback=self._obs_command_running,
            component_state_callback=self._component_state_changed,
            admin_mode_callback=self._perform_action,
        )

    # --------
    # Commands
    # --------

    class InitCommand(CbfObsDevice.InitCommand):
        """
        A class for the Vcc's init_device() "command".
        """

        def do(
            self: Vcc.InitCommand,
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
            self._device._subarray_membership = 0

            self._device.set_change_event("dishID", True)
            self._device.set_archive_event("dishID", True)
            self._device.set_change_event("frequencyBand", True)
            self._device.set_archive_event("frequencyBand", True)
            self._device.set_change_event("subarrayMembership", True)
            self._device.set_archive_event("subarrayMembership", True)

            return (result_code, msg)

    # ---------------------
    # Long Running Commands
    # ---------------------

    @command(
        dtype_in="DevString",
        dtype_out="DevVarLongStringArray",
        doc_in="Band config string.",
    )
    @tango.DebugIt()
    def ConfigureBand(
        self: Vcc, band_config: str
    ) -> DevVarLongStringArrayType:
        """
        Turn on the corresponding band device and disable all the others.

        :param band_config: json string containing: the frequency band name,
                            dish sample rate, and number of samples per frame

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: DevVarLongStringArrayType
        """
        command_handler = self.get_command_object(command_name="ConfigureBand")
        result_code, command_id = command_handler(band_config)
        return [[result_code], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return Vcc.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
