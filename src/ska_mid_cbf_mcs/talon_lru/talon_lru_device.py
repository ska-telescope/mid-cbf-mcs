# -*- coding: utf-8 -*-
#
# This file is part of the TalonLRU project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" 
TANGO device class for controlling and monitoring a Talon LRU.
"""

from __future__ import annotations
import threading
from typing import Any

# tango imports
import tango
from tango import DebugIt, DeviceProxy
from tango.server import run
from tango.server import Device, DeviceMeta
from tango.server import attribute, command
from tango.server import device_property
from tango import AttrQuality, DispLevel, DevState
from tango import AttrWriteType, PipeWriteType
from ska_tango_base import SKABaseDevice

# Additional import
# PROTECTED REGION ID(TalonLRU.additionnal_import) ENABLED START #
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.commons.global_enum import PowerMode
from ska_tango_base.commands import ResultCode
# PROTECTED REGION END #    //  TalonLRU.additionnal_import

__all__ = ["TalonLRU", "main"]

class TalonLRU(SKABaseDevice):
    """
    TANGO device class for controlling and monitoring a Talon LRU
    """
    # PROTECTED REGION ID(TalonLRU.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  TalonLRU.class_variable

    # -----------------
    # Device Properties
    # -----------------

    TalonDxBoard1Address = device_property(
        dtype='str',
    )

    TalonDxBoard2Address = device_property(
        dtype='str',
    )

    PDU1Address = device_property(
        dtype='str',
    )

    PDU1PowerOutlet = device_property(
        dtype='int',
    )

    PDU2Address = device_property(
        dtype='str',
    )

    PDU2PowerOutlet = device_property(
        dtype='int',
    )

    # ----------
    # Attributes
    # ----------

    PDU1PowerMode = attribute(
        dtype='uint16',
        doc="Power mode of the Talon LRU PSU 1",
    )

    PDU2PowerMode = attribute(
        dtype='uint16',
        doc="Power mode of the Talon LRU PSU 2",
    )

    # ---------------
    # General methods
    # ---------------

    def always_executed_hook(self: TalonLRU) -> None:
        # PROTECTED REGION ID(TalonLRU.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonLRU.always_executed_hook

    def delete_device(self: TalonLRU) -> None:
        # PROTECTED REGION ID(TalonLRU.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonLRU.delete_device

    def init_command_objects(self: TalonLRU) -> None:
        """
        Sets up the command objects.
        """
        super().init_command_objects()

        device_args = (self, self.state_model, self.logger)
        self.register_command_object(
            "On", self.OnCommand(*device_args)
        )
        self.register_command_object(
            "Off", self.OffCommand(*device_args)
        )

    # ------------------
    # Attributes methods
    # ------------------

    def read_PDU1PowerMode(self: TalonLRU) -> PowerMode:
        return self._pdu1_power_mode

    def read_PDU2PowerMode(self: TalonLRU) -> PowerMode:
        return self._pdu2_power_mode

    # --------
    # Commands
    # --------

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonLRU's init_device() "command".
        """
        def do(self: TalonLRU.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            super().do()

            device = self.target
            device._power_switch_lock = threading.Lock()

            # Get the device proxies of all the devices we care about
            device._proxy_talondx_board1 = self.get_device_proxy(device.TalonDxBoard1Address)
            device._proxy_talondx_board2 = self.get_device_proxy(device.TalonDxBoard2Address)
            device._proxy_power_switch1 = self.get_device_proxy(device.PDU1Address)
            if device.PDU2Address == device.PDU1Address:
                device._proxy_power_switch2 = device._proxy_power_switch1
            else:
                device._proxy_power_switch2 = self.get_device_proxy(device.PDU2Address)

            # Subscribe to simulationMode change event and increase the access
            # timeout of the power switch proxies, since the HTTP connection
            # timeout must be >3s.
            if device._proxy_power_switch1 is not None:
                device._proxy_power_switch1.set_timeout_millis(5000)
                device._proxy_power_switch1.add_change_event_callback("simulationMode",
                    device._check_power_mode_callback, stateless=True)

            if device.PDU2Address != device.PDU1Address and device._proxy_power_switch2 is not None:
                device._proxy_power_switch2.set_timeout_millis(5000)
                device._proxy_power_switch2.add_change_event_callback("simulationMode",
                    device._check_power_mode_callback, stateless=True)

            if device.get_state() == DevState.INIT:
                return (ResultCode.OK, "TalonLRU initialization OK")
            else:
                return (ResultCode.FAILED, "One or both PDU outlets have incorrect initial power state")
        
        def get_device_proxy(self: TalonLRU.InitCommand, fqdn: str) -> DeviceProxy | None:
            """
            Attempt to get a device proxy of the specified device.

            :param fqdn: FQDN of the device to connect to
            :return: DeviceProxy to the device or None if no connection was made
            """
            try:
                self.logger.info(f"Attempting connection to {fqdn} device")
                device_proxy = CbfDeviceProxy(fqdn=fqdn, logger=self.logger, connect=False)
                device_proxy.connect(max_time=0) # Make one attempt at connecting
                return device_proxy
            except tango.DevFailed as df:
                for item in df.args:
                    self.logger.error(f"Failed connection to {fqdn} device: {item.reason}")
                return None

    def _check_power_mode_callback(
        self: TalonLRU,
        fqdn: str = '',
        name: str = '',
        value: Any = None,
        quality: tango.AttrQuality = None
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state.
        """
        with self._power_switch_lock:
            if self._proxy_power_switch1 is not None:
                if self._proxy_power_switch1.numOutlets != 0:
                    self._pdu1_power_mode = self._proxy_power_switch1.GetOutletPowerMode(self.PDU1PowerOutlet)
                else:
                    self._pdu1_power_mode = PowerMode.UNKNOWN
            else:
                self._pdu1_power_mode = PowerMode.UNKNOWN

            if self._proxy_power_switch2 is not None:
                if self._proxy_power_switch2.numOutlets != 0:
                    self._pdu2_power_mode = self._proxy_power_switch2.GetOutletPowerMode(self.PDU2PowerOutlet)
                else:
                    self._pdu2_power_mode = PowerMode.UNKNOWN
            else:
                self._pdu2_power_mode = PowerMode.UNKNOWN

            # Check the expected power mode
            dev_state = self.get_state()
            if dev_state == DevState.INIT or dev_state == DevState.OFF:
                expected_power_mode = PowerMode.OFF
            elif dev_state == DevState.ON:
                expected_power_mode = PowerMode.ON
            else:
                # In other device states, we don't know what the expected power
                # mode should be. Don't check it.
                return
                
            if (self._pdu1_power_mode == expected_power_mode and
                self._pdu2_power_mode == expected_power_mode):
                return

            if self._pdu1_power_mode != expected_power_mode:
                self.logger.error(
                    f"PDU outlet 1 expected power mode: ({expected_power_mode})," \
                    f" actual power mode: ({self._pdu1_power_mode})")

            if self._pdu2_power_mode != expected_power_mode:
                self.logger.error(
                    f"PDU outlet 2 expected power mode: ({expected_power_mode})," \
                    f" actual power mode: ({self._pdu1_power_mode})")

            self.set_state(DevState.FAULT)
            self.set_status("The device is in FAULT state - one or both PDU outlets have incorrect power state.")

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.

        Turn on both outlets that provide power to the LRU. Device is put into
        ON state if at least one outlet was successfully turned on.
        """

        def do(self: TalonLRU.OnCommand) -> tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            device = self.target

            with device._power_switch_lock:
                # Check that this command is still allowed since the
                # _check_power_mode_callback could have changed the state
                self.check_allowed()

                # Power on both outlets
                result1 = ResultCode.FAILED
                if device._proxy_power_switch1 is not None:
                    result1 = device._proxy_power_switch1.TurnOnOutlet(device.PDU1PowerOutlet)[0][0]
                    if result1 == ResultCode.OK:
                        device._pdu1_power_mode = PowerMode.ON
                        self.logger.info("PDU 1 successfully turned on.")

                result2 = ResultCode.FAILED
                if device._proxy_power_switch2 is not None:
                    result2 = device._proxy_power_switch2.TurnOnOutlet(device.PDU2PowerOutlet)[0][0]
                    if result2 == ResultCode.OK:
                        device._pdu2_power_mode = PowerMode.ON
                        self.logger.info("PDU 2 successfully turned on.")

                # Determine what result code to return
                if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
                    return ResultCode.FAILED, "Failed to turn on both outlets"
                elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
                    device.set_state(DevState.ON)
                    return ResultCode.OK, "Only one outlet successfully turned on"
                else:
                    device.set_state(DevState.ON)
                    return ResultCode.OK, "Both outlets successfully turned on"

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.

        Turn off both outlets that provide power to the LRU. Device is put in
        the OFF state if both outlets were successfully turned off.
        """

        def do(self: TalonLRU.OffCommand) -> tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            device = self.target

            with device._power_switch_lock:
                # Check that this command is still allowed since the
                # _check_power_mode_callback could have changed the state
                self.check_allowed()

                # Power off both outlets
                result1 = ResultCode.FAILED
                if device._proxy_power_switch1 is not None:
                    result1 = device._proxy_power_switch1.TurnOffOutlet(device.PDU1PowerOutlet)[0][0]
                    if result1 == ResultCode.OK:
                        device._pdu1_power_mode = PowerMode.OFF
                        self.logger.info("PSU 1 successfully turned off.")

                result2 = ResultCode.FAILED
                if device._proxy_power_switch2 is not None:
                    result2 = device._proxy_power_switch2.TurnOffOutlet(device.PDU2PowerOutlet)[0][0]
                    if result2 == ResultCode.OK:
                        device._pdu2_power_mode = PowerMode.OFF
                        self.logger.info("PSU 2 successfully turned off.")

                # Determine what result code to return
                if result1 == ResultCode.FAILED and result2 == ResultCode.FAILED:
                    return ResultCode.FAILED, "Failed to turn off both outlets"
                elif result1 == ResultCode.FAILED or result2 == ResultCode.FAILED:
                    return ResultCode.FAILED, "Only one outlet successfully turned off"
                else:
                    device.set_state(DevState.OFF)
                    return ResultCode.OK, "Both outlets successfully turned off"

# ----------
# Run server
# ----------

def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonLRU.main) ENABLED START #
    return run((TalonLRU,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonLRU.main

if __name__ == '__main__':
    main()
