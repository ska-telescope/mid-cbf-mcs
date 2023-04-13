# -*- coding: utf-8 -*-
#
#
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
TANGO device class for monitoring a Talon board.
"""

from __future__ import annotations

from typing import Optional

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerMode
from tango import AttrWriteType
from tango.server import attribute, device_property, run

from ska_mid_cbf_mcs.component.component_manager import CommunicationStatus
from ska_mid_cbf_mcs.talon_board.talon_board_component_manager import (
    TalonBoardComponentManager,
)

# Additional import
# PROTECTED REGION ID(TalonBoard.additionnal_import) ENABLED START #


# PROTECTED REGION END #    //  TalonBoard.additionnal_import

__all__ = ["TalonBoard", "main"]


class TalonBoard(SKABaseDevice):
    """
    TANGO device class for consuming logs from the Tango devices run on the Talon boards,
    converting them to the SKA format, and outputting them via the logging framework.
    """

    # PROTECTED REGION ID(TalonBoard.class_variable) ENABLED START #
    # PROTECTED REGION END #    //  TalonBoard.class_variable

    # -----------------
    # Device Properties
    # -----------------

    TalonDxBoardAddress = device_property(dtype="str")

    InfluxDbPort = device_property(dtype="DevULong")

    InfluxDbOrg = device_property(dtype="str")

    InfluxDbBucket = device_property(dtype="str")

    InfluxDbAuthToken = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------
    @attribute(dtype=float, label="FPGA Die Temperature", doc="FPGA Die Temperature")
    def FpgaDieTemperature(self: TalonBoard) -> float:
        """
        Read the FPGA die temperature of the Talon-DX board.

        :return: the FPGA die temperature in deg Celcius
        """
        res = self.component_manager.fpga_die_temperature()
        return res

    @attribute(dtype=float, label="Humidity Sensor Temperature", doc="Humidity Sensor Temperature")
    def HumiditySensorTemperature(self: TalonBoard) -> float:
        """
        Read the humidity sensor temperature of the Talon-DX board.

        :return: the humidity sensor temperature in deg Celcius
        """
        return self.component_manager.humidity_sensor_temperature()

    @attribute(dtype=(float,), max_dim_x=4, label="DIMM Memory Module Temperatures", doc="DIMM Memory Module Temperatures. Array of size 4. Value set to 0 if not valid.")
    def DIMMTemperatures(self: TalonBoard):
        """
        Read the DIMM temperatures of the Talon-DX board.

        :return: the DIMM temperatures in deg Celcius
        """
        return self.component_manager.dimm_temperatures()

    @attribute(dtype=(float,), max_dim_x=5, label="MBO Tx Temperatures", doc="MBO Tx Temperatures. Array of size 5. Value set to 0 if not valid.")
    def MboTxTemperatures(self: TalonBoard):
        """
        Read the MBO Tx temperatures of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx temperatures in deg Celcius.
        """
        return self.component_manager.mbo_tx_temperatures()

    @attribute(dtype=(float,), max_dim_x=5, label="MBO Rx VCC 3.3 Voltages", doc="MBO Rx VCC 3.3 Voltages. Array of size 5. Value set to 0 if not valid.")
    def MboRxVccVoltages(self: TalonBoard):
        """
        Read the MBO Tx temperatures of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx temperatures in deg Celcius.
        """
        return self.component_manager.mbo_rx_vcc_voltages()

    @attribute(dtype=(int,), max_dim_x=4, label="Fan PWM values", doc="Fan PWM values. Array of size 4.")
    def FansPwm(self: TalonBoard):
        """
        Read the PWM value of the fans. Valid values are
        0 to 255.

        :return: the PWM value of the fans
        """
        return self.component_manager.fans_pwm()

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: TalonBoard) -> None:
        # PROTECTED REGION ID(TalonBoard.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonBoard.always_executed_hook

    def delete_device(self: TalonBoard) -> None:
        # PROTECTED REGION ID(TalonBoard.delete_device) ENABLED START #
        pass
        # PROTECTED REGION END #    //  TalonBoard.delete_device

    def init_command_objects(self: TalonBoard) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        device_args = (self, self.op_state_model, self.logger)

        self.register_command_object("On", self.OnCommand(*device_args))

        self.register_command_object("Off", self.OffCommand(*device_args))

    # ----------
    # Callbacks
    # ----------

    def _communication_status_changed(
        self: TalonLRU,
        communication_status: CommunicationStatus,
    ) -> None:
        """
        Handle change in communications status between component manager and component.

        This is a callback hook, called by the component manager when
        the communications status changes. It is implemented here to
        drive the op_state.

        :param communication_status: the status of communications
            between the component manager and its component.
        """

        self._communication_status = communication_status

        if communication_status == CommunicationStatus.DISABLED:
            self.op_state_model.perform_action("component_disconnected")
        elif communication_status == CommunicationStatus.NOT_ESTABLISHED:
            self.op_state_model.perform_action("component_unknown")

    def _component_power_mode_changed(
        self: TalonLRU,
        power_mode: PowerMode,
    ) -> None:
        """
        Handle change in the power mode of the component.

        This is a callback hook, called by the component manager when
        the power mode of the component changes. It is implemented here
        to drive the op_state.

        :param power_mode: the power mode of the component.
        """
        self._component_power_mode = power_mode

        if self._communication_status == CommunicationStatus.ESTABLISHED:
            action_map = {
                PowerMode.OFF: "component_off",
                PowerMode.STANDBY: "component_standby",
                PowerMode.ON: "component_on",
                PowerMode.UNKNOWN: "component_unknown",
            }

            self.op_state_model.perform_action(action_map[power_mode])

    def _component_fault(self: TalonLRU, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status(
                "The device is in FAULT state - one or both PDU outlets have incorrect power state."
            )

    def _check_power_mode(
        self: TalonLRUComponentManager,
        fqdn: str = "",
        name: str = "",
        value: Any = None,
        quality: tango.AttrQuality = None,
    ) -> None:
        """
        Get the power mode of both PDUs and check that it is consistent with the
        current device state. This is a callback that gets called whenever simulationMode
        changes in the power switch devices.
        """
        with self._power_switch_lock:
            self.component_manager.check_power_mode(self.get_state())

    # --------
    # Commands
    # --------

    def create_component_manager(
        self: TalonBoard,
    ) -> TalonBoardComponentManager:
        """
        Create and return a component manager for this device.

        :return: a component manager for this device.
        """

        self.logger.debug("Entering create_component_manager()")

        self._communication_status: Optional[CommunicationStatus] = None
        self._component_power_mode: Optional[PowerMode] = None

        return TalonBoardComponentManager(
            hostname=self.TalonDxBoardAddress,
            influx_port=self.InfluxDbPort,
            influx_org=self.InfluxDbOrg,
            influx_bucket=self.InfluxDbBucket,
            influx_auth_token=self.InfluxDbAuthToken,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
            check_power_mode_callback=self._check_power_mode,
        )

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonBoard's init_device() "command".
        """

        def do(self: TalonBoard.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            return super().do()


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonBoard.main) ENABLED START #
    return run((TalonBoard,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonBoard.main


if __name__ == "__main__":
    main()
