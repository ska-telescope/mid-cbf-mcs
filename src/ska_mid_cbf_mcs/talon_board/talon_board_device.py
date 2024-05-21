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

# tango imports
from ska_tango_base import SKABaseDevice
from ska_tango_base.commands import ResultCode, SubmittedSlowCommand
from tango import (
    DebugIt,
    DevVarBooleanArray,
    DevVarFloatArray,
    DevVarShortArray,
)
from tango.server import attribute, command, device_property

from ska_mid_cbf_mcs.device.base_device import CbfDevice
from ska_mid_cbf_mcs.talon_board.talon_board_component_manager import (
    TalonBoardComponentManager,
)

# Additional import

__all__ = ["TalonBoard", "main"]


class TalonBoard(CbfDevice):
    """
    TANGO device class for consuming logs from the Tango devices run on the Talon boards,
    converting them to the SKA format, and outputting them via the logging framework.
    """

    # -----------------
    # Device Properties
    # -----------------

    TalonDxBoardAddress = device_property(dtype="str")

    InfluxDbPort = device_property(dtype="DevULong")

    InfluxDbOrg = device_property(dtype="str")

    InfluxDbBucket = device_property(dtype="str")

    InfluxDbAuthToken = device_property(dtype="str")

    Instance = device_property(dtype="str")

    TalonDxSysIdAddress = device_property(dtype="str")

    TalonDx100GEthernetAddress = device_property(dtype="str")

    TalonStatusAddress = device_property(dtype="str")

    HpsMasterAddress = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    @attribute(
        dtype=str,
        label="Subarray ID",
        doc="The Subarray ID assigned to the board. This attribute is only used for labelling.",
    )
    def subarrayID(self: TalonBoard) -> str:
        """
        Read the subarrayID attribute.

        :return: the vcc ID
        :rtype: str
        """
        return self._subarrayID

    @subarrayID.write
    def subarrayID(self: TalonBoard, value: str) -> None:
        """
        Write the subarrayID attribute.

        :param value: the vcc ID
        """
        self._subarrayID = value

    @attribute(
        dtype=str,
        label="Dish ID",
        doc="The Dish ID assigned to the board. This attribute is only used for labelling.",
    )
    def dishID(self: TalonBoard) -> str:
        """
        Read the dishID attribute.

        :return: the Dish ID
        :rtype: str
        """
        return self._dishID

    @dishID.write
    def dishID(self: TalonBoard, value: str) -> None:
        """
        Write the dishID attribute.

        :param value: the Dish ID
        """
        self._dishID = value

    @attribute(
        dtype=str,
        label="VCC ID",
        doc="The VCC ID assigned to the board. This attribute is only used for labelling.",
    )
    def vccID(self: TalonBoard) -> str:
        """
        Read the vccID attribute.

        :return: the VCC ID
        :rtype: str
        """
        return self._vccID

    @vccID.write
    def vccID(self: TalonBoard, value: str) -> None:
        """
        Write the vccID attribute.

        :param value: the VCC ID
        """
        self._vccID = value

    @attribute(dtype=str, label="IP", doc="IP Address")
    def ipAddr(self: TalonBoard) -> str:
        """
        The IP Address assigned to this talon board. This is a device
        property. This attribute is a workaround to expose it
        to Taranta dashboards.

        :return: the IP address
        """
        return self.TalonDxBoardAddress

    # TalonSysID Attr
    @attribute(
        dtype=str, label="FPGA bitstream version", doc="FPGA bitstream version"
    )
    def bitstreamVersion(self: TalonBoard) -> str:
        """
        Read the FPGA bitstream version of the Talon-DX board.

        :return: the FPGA bitstream version
        """
        res = self.component_manager.talon_sysid_version()
        return res

    @attribute(
        dtype=int,
        label="FPGA bitstream checksum",
        doc="FPGA bitstream checksum",
    )
    def bitstreamChecksum(self: TalonBoard) -> int:
        """
        Read the least 32 bits of md5 checksum of the bitstream name

        :return: a 32 bit unique identifier for the bitstream
        """
        res = self.component_manager.talon_sysid_bitstream()
        return res

    # TalonStatus Attr
    @attribute(
        dtype=bool, label="iopll_locked_fault", doc="iopll_locked_fault"
    )
    def iopllLockedFault(self: TalonBoard) -> bool:
        """
        Read the iopll_locked_fault status

        :return: the iopll_locked_fault status
        """
        res = self.component_manager.talon_status_iopll_locked_fault()
        return res

    @attribute(
        dtype=bool, label="fs_iopll_locked_fault", doc="fs_iopll_locked_fault"
    )
    def fsIopllLockedFault(self: TalonBoard) -> bool:
        """
        Read the fs_iopll_locked_fault status

        :return: the fs_iopll_locked_fault status
        """
        res = self.component_manager.talon_status_fs_iopll_locked_fault()
        return res

    @attribute(
        dtype=bool,
        label="comms_iopll_locked_fault",
        doc="comms_iopll_locked_fault",
    )
    def commsIopllLockedFault(self: TalonBoard) -> bool:
        """
        Read the comms_iopll_locked_fault status

        :return: the comms_iopll_locked_fault status
        """
        res = self.component_manager.talon_status_comms_iopll_locked_fault()
        return res

    @attribute(dtype=bool, label="system_clk_fault", doc="system_clk_fault")
    def systemClkFault(self: TalonBoard) -> bool:
        """
        Read the system_clk_fault status

        :return: the system_clk_fault status
        """
        res = self.component_manager.talon_status_system_clk_fault()
        return res

    @attribute(dtype=bool, label="emif_bl_fault", doc="emif_bl_fault")
    def emifBlFault(self: TalonBoard) -> bool:
        """
        Read the emif_bl_fault status

        :return: the emif_bl_fault status
        """
        res = self.component_manager.talon_status_emif_bl_fault()
        return res

    @attribute(dtype=bool, label="emif_br_fault", doc="emif_br_fault")
    def emifBrFault(self: TalonBoard) -> bool:
        """
        Read the emif_br_fault status

        :return: the emif_br_fault status
        """
        res = self.component_manager.talon_status_emif_br_fault()
        return res

    @attribute(dtype=bool, label="emif_tr_fault", doc="emif_tr_fault")
    def emifTrFault(self: TalonBoard) -> bool:
        """
        Read the emif_tr_fault status

        :return: the emif_tr_fault status
        """
        res = self.component_manager.talon_status_emif_tr_fault()
        return res

    @attribute(dtype=bool, label="e100g_0_pll_fault", doc="e100g_0_pll_fault")
    def ethernet0PllFault(self: TalonBoard) -> bool:
        """
        Read the e100g_0_pll_fault status

        :return: the e100g_0_pll_fault status
        """
        res = self.component_manager.talon_status_e100g_0_pll_fault()
        return res

    @attribute(dtype=bool, label="e100g_1_pll_fault", doc="e100g_1_pll_fault")
    def ethernet1PllFault(self: TalonBoard) -> bool:
        """
        Read the e100g_1_pll_fault status

        :return: the e100g_1_pll_fault status
        """
        res = self.component_manager.talon_status_e100g_1_pll_fault()
        return res

    @attribute(dtype=bool, label="slim_pll_fault", doc="slim_pll_fault")
    def slimPllFault(self: TalonBoard) -> bool:
        """
        Read the slim_pll_fault status

        :return: the slim_pll_fault status
        """
        res = self.component_manager.talon_status_slim_pll_fault()
        return res

    @attribute(
        dtype=float, label="FPGA Die Temperature", doc="FPGA Die Temperature"
    )
    def fpgaDieTemperature(self: TalonBoard) -> float:
        """
        Read the FPGA die temperature of the Talon-DX board.

        :return: the FPGA die temperature in deg Celcius
        """
        res = self.component_manager.fpga_die_temperature()
        return res

    @attribute(
        dtype=float,
        label="Humidity Sensor Temperature",
        doc="Humidity Sensor Temperature",
    )
    def humiditySensorTemperature(self: TalonBoard) -> float:
        """
        Read the humidity sensor temperature of the Talon-DX board.

        :return: the humidity sensor temperature in deg Celcius
        """
        return self.component_manager.humidity_sensor_temperature()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="DIMM Memory Module Temperatures",
        doc="DIMM Memory Module Temperatures. Array of size 4. Value set to 0 if not valid.",
    )
    def dimmTemperatures(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the DIMM temperatures of the Talon-DX board.

        :return: the DIMM temperatures in deg Celcius
        """
        return self.component_manager.dimm_temperatures()

    @attribute(
        dtype=[float],
        max_dim_x=5,
        label="MBO Tx Temperatures",
        doc="MBO Tx Temperatures. Value set to 0 if not valid.",
    )
    def mboTxTemperatures(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the MBO Tx temperatures of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx temperatures in deg Celcius.
        """
        return self.component_manager.mbo_tx_temperatures()

    @attribute(
        dtype=[float],
        max_dim_x=5,
        label="MBO Tx VCC 3.3 Voltages",
        doc="MBO Tx VCC 3.3 Voltages. Value set to 0 if not valid.",
    )
    def mboTxVccVoltages(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the MBO Tx VCC 3.3V voltages of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx VCC voltages.
        """
        return self.component_manager.mbo_tx_vcc_voltages()

    @attribute(
        dtype=[bool],
        max_dim_x=5,
        label="MBO Tx Fault Status",
        doc="MBO Tx Fault Status. True = status set.",
    )
    def mboTxFaultStatus(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the MBO Tx fault status register of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Fault Status Flag.
        """
        return self.component_manager.mbo_tx_fault_status()

    @attribute(
        dtype=[bool],
        max_dim_x=5,
        label="MBO Tx Loss of Lock Status",
        doc="MBO Tx Loss of Lock Status. True = status set.",
    )
    def mboTxLolStatus(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the MBO Tx loss of lock status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Loss of Lock Status Flag.
        """
        return self.component_manager.mbo_tx_lol_status()

    @attribute(
        dtype=[bool],
        max_dim_x=5,
        label="MBO Tx Loss of Signal Status",
        doc="MBO Tx Loss of Signal Status. True = status set.",
    )
    def mboTxLosStatus(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the MBO Tx loss of signal status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Loss of Signal Status Flag.
        """
        return self.component_manager.mbo_tx_los_status()

    @attribute(
        dtype=[float],
        max_dim_x=5,
        label="MBO Rx VCC 3.3 Voltages",
        doc="MBO Rx VCC 3.3 Voltages. Value set to 0 if not valid.",
    )
    def mboRxVccVoltages(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the MBO Rx VCC 3.3V voltages of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Rx VCC voltages.
        """
        return self.component_manager.mbo_rx_vcc_voltages()

    @attribute(
        dtype=[bool],
        max_dim_x=5,
        label="MBO Rx Loss of Lock Status",
        doc="MBO Rx Loss of Lock Status. True = status set.",
    )
    def mboRxLolStatus(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the MBO Rx loss of lock status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Rx Loss of Lock Status Flag.
        """
        return self.component_manager.mbo_rx_lol_status()

    @attribute(
        dtype=[bool],
        max_dim_x=5,
        label="MBO Rx Loss of Signal Status",
        doc="MBO Rx Loss of Signal Status. True = status set.",
    )
    def mboRxLosStatus(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the MBO Rx loss of signal status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Rx Loss of Signal Status Flag.
        """
        return self.component_manager.mbo_rx_los_status()

    @attribute(
        dtype=[int],
        max_dim_x=4,
        label="Fan PWM values",
        doc="Fan PWM values.",
    )
    def fansPwm(self: TalonBoard) -> DevVarShortArray:
        """
        Read the PWM value of the fans. Valid values are
        0 to 255.

        :return: the PWM value of the fans
        """
        return self.component_manager.fans_pwm()

    @attribute(
        dtype=[int],
        max_dim_x=4,
        label="Fan PWM enable values",
        doc="Fan PWM enable values.",
    )
    def fansPwmEnable(self: TalonBoard) -> DevVarShortArray:
        """
        Read the PWM value of the fans. Valid values are 0 to 2.

        :return: the PWM enable value of the fans
        """
        return self.component_manager.fans_pwm_enable()

    @attribute(
        dtype=[bool],
        max_dim_x=4,
        label="Fan Fault status",
        doc="Fan Fault status.",
    )
    def fansFault(self: TalonBoard) -> DevVarBooleanArray:
        """
        Read the fault status of the fans.

        :return: true if fan fault register is set
        """
        return self.component_manager.fans_fault()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Input Voltage",
        doc="LTM Input Voltage. One entry per LTM.",
    )
    def ltmInputVoltage(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the input voltage to LTMs

        :return: the input voltage to LTMs
        """
        return self.component_manager.ltm_input_voltage()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Output Voltage 1",
        doc="LTM Output Voltage 1. One entry per LTM",
    )
    def ltmOutputVoltage1(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the output voltage 1 to LTMs

        :return: the output voltage 1 to LTMs
        """
        return self.component_manager.ltm_output_voltage_1()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Output Voltage 2",
        doc="LTM Output Voltage 2. One entry per LTM",
    )
    def ltmOutputVoltage2(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the output voltage 2 to LTMs

        :return: the output voltage 2 to LTMs
        """
        return self.component_manager.ltm_output_voltage_2()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Input Current",
        doc="LTM Input Current. One entry per LTM.",
    )
    def ltmInputCurrent(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the input current to LTMs

        :return: the input current to LTMs
        """
        return self.component_manager.ltm_input_current()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Output Current 1",
        doc="LTM Output Current 1. One entry per LTM",
    )
    def ltmOutputCurrent1(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the output current 1 to LTMs

        :return: the output current 1 to LTMs
        """
        return self.component_manager.ltm_output_current_1()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Output Current 2",
        doc="LTM Output Current 2. One entry per LTM",
    )
    def ltmOutputCurrent2(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the output current 2 to LTMs

        :return: the output current 2 to LTMs
        """
        return self.component_manager.ltm_output_current_2()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Temperature 1",
        doc="LTM Temperature 1. One entry per LTM",
    )
    def ltmTemperature1(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the temperature 1 of LTMs

        :return: the temperature 1 of LTMs
        """
        return self.component_manager.ltm_temperature_1()

    @attribute(
        dtype=[float],
        max_dim_x=4,
        label="LTM Temperature 2",
        doc="LTM Temperature 2. One entry per LTM",
    )
    def ltmTemperature2(self: TalonBoard) -> DevVarFloatArray:
        """
        Read the temperature 2 of LTMs

        :return: the temperature 2 of LTMs
        """
        return self.component_manager.ltm_temperature_2()

    @attribute(
        dtype=[bool],
        max_dim_x=4,
        label="LTM Voltage Warning",
        doc="True if any input or output voltage warnings is set. One entry per LTM",
    )
    def ltmVoltageWarning(self: TalonBoard) -> DevVarBooleanArray:
        """
        Returns True if any input or output voltage warning is set. One entry per LTM

        :return: True if any input or output voltage warning is set
        """
        return self.component_manager.ltm_voltage_warning()

    @attribute(
        dtype=[bool],
        max_dim_x=4,
        label="LTM Current Warning",
        doc="True if any input or output current warnings is set. One entry per LTM",
    )
    def ltmCurrentWarning(self: TalonBoard) -> DevVarBooleanArray:
        """
        Returns True if any input or output current warning is set. One entry per LTM

        :return: True if any input or output current warning is set
        """
        return self.component_manager.ltm_current_warning()

    @attribute(
        dtype=[bool],
        max_dim_x=4,
        label="LTM Temperature Warning",
        doc="True if any temperature warnings is set. One entry per LTM",
    )
    def ltmTemperatureWarning(self: TalonBoard) -> DevVarBooleanArray:
        """
        Returns True if any temperature warning is set. One entry per LTM

        :return: True if any temperature warning is set
        """
        return self.component_manager.ltm_temperature_warning()

    # ---------------
    # General methods
    # ---------------
    def always_executed_hook(self: TalonBoard) -> None:
        pass

    def delete_device(self: TalonBoard) -> None:
        pass

    def init_command_objects(self: TalonBoard) -> None:
        """
        Sets up the command objects
        """
        super().init_command_objects()

        self.register_command_object(
            "On",
            SubmittedSlowCommand(
                command_name="On",
                command_tracker=self._command_tracker,
                component_manager=self.component_manager,
                method_name="on",
                logger=self.logger,
            ),
        )

    # ----------
    # Callbacks
    # ----------

    # None at this time...
    # We currently rely on the SKABaseDevice implemented callbacks.

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

        return TalonBoardComponentManager(
            hostname=self.TalonDxBoardAddress,
            influx_port=self.InfluxDbPort,
            influx_org=self.InfluxDbOrg,
            influx_bucket=self.InfluxDbBucket,
            influx_auth_token=self.InfluxDbAuthToken,
            instance=self.Instance,
            talon_sysid_address=self.TalonDxSysIdAddress,
            eth_100g_address=self.TalonDx100GEthernetAddress,
            talon_status_address=self.TalonStatusAddress,
            hps_master_address=self.HpsMasterAddress,
            logger=self.logger,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    class InitCommand(SKABaseDevice.InitCommand):
        """
        A class for the TalonBoard's init_device() "command".
        """
        
        # Some of these IDs are typically integers. But it is easier to use
        # empty string to show the board is not assigned.
        _subarrayID = ""
        _dishID = ""
        _vccID = ""

        def do(self: TalonBoard.InitCommand) -> tuple[ResultCode, str]:
            """
            Stateless hook for device initialisation.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            return super().do()


# ---------------------
# Long Running Commands
# ---------------------


def is_On_allowed(self: TalonBoard) -> bool:
    return True


@command(
    dtype_out="DevVarLongStringArray",
    doc_out="Tuple of a string containing a return code and message indicating the status of the command, as well as the SubmittedSlowCommand's command ID.",
)
@DebugIt()
def On(self: TalonBoard) -> None:
    command_handler = self.get_command_object("On")
    result_code_message, command_id = command_handler()
    return [[result_code_message], [command_id]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    return TalonBoard.run_server(args=args or None, **kwargs)


if __name__ == "__main__":
    main()
