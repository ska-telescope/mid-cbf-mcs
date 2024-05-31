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

from typing import Optional, Tuple

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

    # Some of these IDs are typically integers. But it is easier to use
    # empty string to show the board is not assigned.
    subarrayID_ = ""
    dishID_ = ""
    vccID_ = ""

    # PROTECTED REGION END #    //  TalonBoard.class_variable

    # -----------------
    # Device Properties
    # -----------------

    TalonDxBoardAddress = device_property(dtype="str")

    InfluxDbPort = device_property(dtype="DevULong")

    InfluxDbOrg = device_property(dtype="str")

    InfluxDbBucket = device_property(dtype="str")

    InfluxDbAuthToken = device_property(dtype="str")

    Instance = device_property(dtype="str")

    TalonDxSysIdServer = device_property(dtype="str")

    TalonDx100GEthernetServer = device_property(dtype="str")

    TalonStatusServer = device_property(dtype="str")

    HpsMasterServer = device_property(dtype="str")

    # ----------
    # Attributes
    # ----------

    subarrayID = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Subarray ID",
        doc="The Subarray ID assigned to the board. This attribute is only used for labelling.",
    )

    dishID = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="DISH ID",
        doc="The DISH ID assigned to the board. This attribute is only used for labelling.",
    )

    vccID = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="VCC ID",
        doc="The VCC ID assigned to the board. This attribute is only used for labelling.",
    )

    @attribute(dtype=str, label="IP", doc="IP Address")
    def IpAddr(self: TalonBoard) -> str:
        """
        The IP Address assigned to this talon board. This is a device
        property. This attribute is a workaround to expose it
        to Taranta.

        :return: the IP address
        """
        return self.TalonDxBoardAddress

    @attribute(
        dtype=str, label="FPGA bitstream version", doc="FPGA bitstream version"
    )
    def BitstreamVersion(self: TalonBoard) -> str:
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
    def BitstreamChecksum(self: TalonBoard) -> str:
        """
        Read the least 32 bits of md5 checksum of the bitstream name

        :return: the FPGA bitstream version
        """
        res = self.component_manager.talon_sysid_bitstream()
        return res

    @attribute(
        dtype=bool, label="iopll_locked_fault", doc="iopll_locked_fault"
    )
    def iopll_locked_fault(self: TalonBoard) -> str:
        """
        Read the iopll_locked_fault status

        :return: the iopll_locked_fault status
        """
        res = self.component_manager.talon_status_iopll_locked_fault()
        return res

    @attribute(
        dtype=bool, label="fs_iopll_locked_fault", doc="fs_iopll_locked_fault"
    )
    def fs_iopll_locked_fault(self: TalonBoard) -> str:
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
    def comms_iopll_locked_fault(self: TalonBoard) -> str:
        """
        Read the comms_iopll_locked_fault status

        :return: the comms_iopll_locked_fault status
        """
        res = self.component_manager.talon_status_comms_iopll_locked_fault()
        return res

    @attribute(dtype=bool, label="system_clk_fault", doc="system_clk_fault")
    def system_clk_fault(self: TalonBoard) -> str:
        """
        Read the system_clk_fault status

        :return: the system_clk_fault status
        """
        res = self.component_manager.talon_status_system_clk_fault()
        return res

    @attribute(dtype=bool, label="emif_bl_fault", doc="emif_bl_fault")
    def emif_bl_fault(self: TalonBoard) -> str:
        """
        Read the emif_bl_fault status

        :return: the emif_bl_fault status
        """
        res = self.component_manager.talon_status_emif_bl_fault()
        return res

    @attribute(dtype=bool, label="emif_br_fault", doc="emif_br_fault")
    def emif_br_fault(self: TalonBoard) -> str:
        """
        Read the emif_br_fault status

        :return: the emif_br_fault status
        """
        res = self.component_manager.talon_status_emif_br_fault()
        return res

    @attribute(dtype=bool, label="emif_tr_fault", doc="emif_tr_fault")
    def emif_tr_fault(self: TalonBoard) -> str:
        """
        Read the emif_tr_fault status

        :return: the emif_tr_fault status
        """
        res = self.component_manager.talon_status_emif_tr_fault()
        return res

    @attribute(dtype=bool, label="e100g_0_pll_fault", doc="e100g_0_pll_fault")
    def e100g_0_pll_fault(self: TalonBoard) -> str:
        """
        Read the e100g_0_pll_fault status

        :return: the e100g_0_pll_fault status
        """
        res = self.component_manager.talon_status_e100g_0_pll_fault()
        return res

    @attribute(dtype=bool, label="e100g_1_pll_fault", doc="e100g_1_pll_fault")
    def e100g_1_pll_fault(self: TalonBoard) -> str:
        """
        Read the e100g_1_pll_fault status

        :return: the e100g_1_pll_fault status
        """
        res = self.component_manager.talon_status_e100g_1_pll_fault()
        return res

    @attribute(dtype=bool, label="slim_pll_fault", doc="slim_pll_fault")
    def slim_pll_fault(self: TalonBoard) -> str:
        """
        Read the slim_pll_fault status

        :return: the slim_pll_fault status
        """
        res = self.component_manager.talon_status_slim_pll_fault()
        return res

    @attribute(
        dtype=float, label="FPGA Die Temperature", doc="FPGA Die Temperature"
    )
    def FpgaDieTemperature(self: TalonBoard) -> float:
        """
        Read the FPGA die temperature of the Talon-DX board.

        :return: the FPGA die temperature in deg Celcius
        """
        res = self.component_manager.fpga_die_temperature()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 0",
        doc="Readings from FPGA Die Voltages 0 Sensors on TalonDX",
        unit="V",
        # min_warning=11.5,
        # max_warning=12.5,
        min_alarm=11.0,
        max_alarm=13.0,
    )
    def FpgaDieVoltage0(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_0()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 1",
        doc="Readings from FPGA Die Voltages 1 Sensors on TalonDX",
        unit="V",
        # min_warning=2.88,
        # max_warning=2.12,
        min_alarm=2.38,
        max_alarm=2.62,
    )
    def FpgaDieVoltage1(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_1()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 2",
        doc="Readings from FPGA Die Voltages 2 Sensors on TalonDX",
        unit="V",
        # min_warning=1.27,
        # max_warning=0.47,
        min_alarm=0.77,
        max_alarm=0.97,
    )
    def FpgaDieVoltage2(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_2()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 3",
        doc="Readings from FPGA Die Voltages 3 Sensors on TalonDX",
        unit="V",
        # min_warning=2.21,
        # max_warning=1.39,
        min_alarm=1.71,
        max_alarm=1.89,
    )
    def FpgaDieVoltage3(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_3()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 4",
        doc="Readings from FPGA Die Voltages 4 Sensors on TalonDX",
        unit="V",
        # min_warning=2.21,
        # max_warning=1.39,
        min_alarm=1.71,
        max_alarm=1.89,
    )
    def FpgaDieVoltage4(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_4()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 5",
        doc="Readings from FPGA Die Voltages 5 Sensors on TalonDX",
        unit="V",
        # min_warning=1.37,
        # max_warning=0.43,
        min_alarm=0.87,
        max_alarm=0.93,
    )
    def FpgaDieVoltage5(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_5()
        return res

    @attribute(
        dtype=float,
        label="FPGA Die Voltage 6",
        doc="Readings from FPGA Die Voltages 6 Sensors on TalonDX",
        unit="V",
        # min_warning=2.21,
        # max_warning=1.39,
        min_alarm=1.71,
        max_alarm=1.89,
    )
    def FpgaDieVoltage6(self: TalonBoard) -> list[float]:
        """
        Reads the following FPGA die voltages of the Talon-DX board:
        [0] External Board Voltage (1/11 ratio)
        [1] External Board Voltage (1/3 ratio)
        [2] FPGA Die VCC (1/1000 ratio)
        [3] FPGA Die VCCIO (1/1000 ratio)
        [4] FPGA Die VCCPT (1/1000 ratio)
        [5] FPGA Die VCCERAM (1/1000 ratio)
        [6] FPGA Die VCCADC (1/1000 ratio)

        All values in the spectrum are scaled according the the give ration
        All values are in Volts (V)

        :return: A spectrum ofthe FPGA Die Voltages in Volts(V)
        """
        res = self.component_manager.fpga_die_voltage_6()
        return res

    @attribute(
        dtype=float,
        label="Humidity Sensor Temperature",
        doc="Humidity Sensor Temperature",
    )
    def HumiditySensorTemperature(self: TalonBoard) -> float:
        """
        Read the humidity sensor temperature of the Talon-DX board.

        :return: the humidity sensor temperature in deg Celcius
        """
        return self.component_manager.humidity_sensor_temperature()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="DIMM Memory Module Temperatures",
        doc="DIMM Memory Module Temperatures. Array of size 4. Value set to 0 if not valid.",
    )
    def DIMMTemperatures(self: TalonBoard):
        """
        Read the DIMM temperatures of the Talon-DX board.

        :return: the DIMM temperatures in deg Celcius
        """
        return self.component_manager.dimm_temperatures()

    @attribute(
        dtype=(float,),
        max_dim_x=5,
        label="MBO Tx Temperatures",
        doc="MBO Tx Temperatures. Value set to 0 if not valid.",
    )
    def MboTxTemperatures(self: TalonBoard):
        """
        Read the MBO Tx temperatures of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx temperatures in deg Celcius.
        """
        return self.component_manager.mbo_tx_temperatures()

    @attribute(
        dtype=(float,),
        max_dim_x=5,
        label="MBO Tx VCC 3.3 Voltages",
        doc="MBO Tx VCC 3.3 Voltages. Value set to 0 if not valid.",
    )
    def MboTxVccVoltages(self: TalonBoard):
        """
        Read the MBO Tx VCC 3.3V voltages of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Tx VCC voltages.
        """
        return self.component_manager.mbo_rx_vcc_voltages()

    @attribute(
        dtype=(bool,),
        max_dim_x=5,
        label="MBO Tx Fault Status",
        doc="MBO Tx Fault Status. True = status set.",
    )
    def MboTxFaultStatus(self: TalonBoard):
        """
        Read the MBO Tx fault status register of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Fault Status Flag.
        """
        return self.component_manager.mbo_tx_fault_status()

    @attribute(
        dtype=(bool,),
        max_dim_x=5,
        label="MBO Tx Loss of Lock Status",
        doc="MBO Tx Loss of Lock Status. True = status set.",
    )
    def MboTxLOLStatus(self: TalonBoard):
        """
        Read the MBO Tx loss of lock status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Loss of Lock Status Flag.
        """
        return self.component_manager.mbo_tx_lol_status()

    @attribute(
        dtype=(bool,),
        max_dim_x=5,
        label="MBO Tx Loss of Signal Status",
        doc="MBO Tx Loss of Signal Status. True = status set.",
    )
    def MboTxLOSStatus(self: TalonBoard):
        """
        Read the MBO Tx loss of signal status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Tx Loss of Signal Status Flag.
        """
        return self.component_manager.mbo_tx_los_status()

    @attribute(
        dtype=(float,),
        max_dim_x=5,
        label="MBO Rx VCC 3.3 Voltages",
        doc="MBO Rx VCC 3.3 Voltages. Value set to 0 if not valid.",
    )
    def MboRxVccVoltages(self: TalonBoard):
        """
        Read the MBO Rx VCC 3.3V voltages of the Talon-DX board. Not all
        MBO i2c addresses can be read, in which case a 0 will be
        returned for the MBO.

        :return: the MBO Rx VCC voltages.
        """
        return self.component_manager.mbo_rx_vcc_voltages()

    @attribute(
        dtype=(bool,),
        max_dim_x=5,
        label="MBO Rx Loss of Lock Status",
        doc="MBO Rx Loss of Lock Status. True = status set.",
    )
    def MboRxLOLStatus(self: TalonBoard):
        """
        Read the MBO Rx loss of lock status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Rx Loss of Lock Status Flag.
        """
        return self.component_manager.mbo_rx_lol_status()

    @attribute(
        dtype=(bool,),
        max_dim_x=5,
        label="MBO Rx Loss of Signal Status",
        doc="MBO Rx Loss of Signal Status. True = status set.",
    )
    def MboRxLOSStatus(self: TalonBoard):
        """
        Read the MBO Rx loss of signal status register of the Talon-DX board.
        Not all MBO i2c addresses can be read, in which case false will be
        returned for the MBO.

        :return: the MBO Rx Loss of Signal Status Flag.
        """
        return self.component_manager.mbo_rx_los_status()

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        label="Fan PWM values",
        doc="Fan PWM values.",
    )
    def FansPwm(self: TalonBoard):
        """
        Read the PWM value of the fans. Valid values are
        0 to 255.

        :return: the PWM value of the fans
        """
        return self.component_manager.fans_pwm()

    @attribute(
        dtype=(int,),
        max_dim_x=4,
        label="Fan PWM enable values",
        doc="Fan PWM enable values.",
    )
    def FansPwmEnable(self: TalonBoard):
        """
        Read the PWM value of the fans. Valid values are 0 to 2.

        :return: the PWM enable value of the fans
        """
        return self.component_manager.fans_pwm_enable()

    @attribute(
        dtype=(bool,),
        max_dim_x=4,
        label="Fan Fault status",
        doc="Fan Fault status.",
    )
    def FansFault(self: TalonBoard):
        """
        Read the fault status of the fans.

        :return: true if fan fault register is set
        """
        return self.component_manager.fans_fault()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Input Voltage",
        doc="LTM Input Voltage. One entry per LTM.",
    )
    def LtmInputVoltage(self: TalonBoard):
        """
        Read the input voltage to LTMs

        :return: the input voltage to LTMs
        """
        return self.component_manager.ltm_input_voltage()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Output Voltage 1",
        doc="LTM Output Voltage 1. One entry per LTM",
    )
    def LtmOutputVoltage1(self: TalonBoard):
        """
        Read the output voltage 1 to LTMs

        :return: the output voltage 1 to LTMs
        """
        return self.component_manager.ltm_output_voltage_1()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Output Voltage 2",
        doc="LTM Output Voltage 2. One entry per LTM",
    )
    def LtmOutputVoltage2(self: TalonBoard):
        """
        Read the output voltage 2 to LTMs

        :return: the output voltage 2 to LTMs
        """
        return self.component_manager.ltm_output_voltage_2()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Input Current",
        doc="LTM Input Current. One entry per LTM.",
    )
    def LtmInputCurrent(self: TalonBoard):
        """
        Read the input current to LTMs

        :return: the input current to LTMs
        """
        return self.component_manager.ltm_input_current()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Output Current 1",
        doc="LTM Output Current 1. One entry per LTM",
    )
    def LtmOutputCurrent1(self: TalonBoard):
        """
        Read the output current 1 to LTMs

        :return: the output current 1 to LTMs
        """
        return self.component_manager.ltm_output_current_1()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Output Current 2",
        doc="LTM Output Current 2. One entry per LTM",
    )
    def LtmOutputCurrent2(self: TalonBoard):
        """
        Read the output current 2 to LTMs

        :return: the output current 2 to LTMs
        """
        return self.component_manager.ltm_output_current_2()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Temperature 1",
        doc="LTM Temperature 1. One entry per LTM",
    )
    def LtmTemperature1(self: TalonBoard):
        """
        Read the temperature 1 of LTMs

        :return: the temperature 1 of LTMs
        """
        return self.component_manager.ltm_temperature_1()

    @attribute(
        dtype=(float,),
        max_dim_x=4,
        label="LTM Temperature 2",
        doc="LTM Temperature 2. One entry per LTM",
    )
    def LtmTemperature2(self: TalonBoard):
        """
        Read the temperature 2 of LTMs

        :return: the temperature 2 of LTMs
        """
        return self.component_manager.ltm_temperature_2()

    @attribute(
        dtype=(bool,),
        max_dim_x=4,
        label="LTM Voltage Warning",
        doc="True if any input or output voltage warnings is set. One entry per LTM",
    )
    def LtmVoltageWarning(self: TalonBoard):
        """
        Returns True if any input or output voltage warning is set. One entry per LTM

        :return: True if any input or output voltage warning is set
        """
        return self.component_manager.ltm_voltage_warning()

    @attribute(
        dtype=(bool,),
        max_dim_x=4,
        label="LTM Current Warning",
        doc="True if any input or output current warnings is set. One entry per LTM",
    )
    def LtmCurrentWarning(self: TalonBoard):
        """
        Returns True if any input or output current warning is set. One entry per LTM

        :return: True if any input or output current warning is set
        """
        return self.component_manager.ltm_current_warning()

    @attribute(
        dtype=(bool,),
        max_dim_x=4,
        label="LTM Temperature Warning",
        doc="True if any temperature warnings is set. One entry per LTM",
    )
    def LtmTemperatureWarning(self: TalonBoard):
        """
        Returns True if any temperature warning is set. One entry per LTM

        :return: True if any temperature warning is set
        """
        return self.component_manager.ltm_temperature_warning()

    # -----------------
    # Attribute Methods
    # -----------------

    def read_subarrayID(self: TalonBoard) -> str:
        # PROTECTED REGION ID(TalonBoard.read_subarrayID) ENABLED START #
        """
        Read the subarrayID attribute.

        :return: the vcc ID
        :rtype: str
        """
        return self.subarrayID_
        # PROTECTED REGION END #    //  TalonBoard.subarrayID_read

    def write_subarrayID(self: TalonBoard, value: str) -> None:
        # PROTECTED REGION ID(TalonBoard.subarrayID_write) ENABLED START #
        """
        Write the subarrayID attribute.

        :param value: the vcc ID
        """
        self.subarrayID_ = value
        # PROTECTED REGION END #    //  TalonBoard.subarrayID_write

    def read_dishID(self: TalonBoard) -> str:
        # PROTECTED REGION ID(TalonBoard.read_dishID) ENABLED START #
        """
        Read the dishID attribute.

        :return: the DISH ID
        :rtype: str
        """
        return self.dishID_
        # PROTECTED REGION END #    //  TalonBoard.dishID_read

    def write_dishID(self: TalonBoard, value: str) -> None:
        # PROTECTED REGION ID(TalonBoard.dishID_write) ENABLED START #
        """
        Write the dishID attribute.

        :param value: the DISH ID
        """
        self.dishID_ = value
        # PROTECTED REGION END #    //  TalonBoard.dishID_write

    def read_vccID(self: TalonBoard) -> str:
        # PROTECTED REGION ID(TalonBoard.read_vccID) ENABLED START #
        """
        Read the vccID attribute.

        :return: the vcc ID
        :rtype: str
        """
        return self.vccID_
        # PROTECTED REGION END #    //  TalonBoard.vccID_read

    def write_vccID(self: TalonBoard, value: str) -> None:
        # PROTECTED REGION ID(TalonBoard.vccID_write) ENABLED START #
        """
        Write the vccID attribute.

        :param value: the vcc ID
        """
        self.vccID_ = value
        # PROTECTED REGION END #    //  TalonBoard.vccID_write

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

        # device_args = (self, self.op_state_model, self.logger)

        # self.register_command_object("On", self.OnCommand(*device_args))

        # self.register_command_object("Off", self.OffCommand(*device_args))

    # ----------
    # Callbacks
    # ----------

    def _communication_status_changed(
        self: TalonBoard, communication_status: CommunicationStatus
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
        self: TalonBoard, power_mode: PowerMode
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

    def _component_fault(self: TalonBoard, faulty: bool) -> None:
        """
        Handle component fault
        """
        if faulty:
            self.op_state_model.perform_action("component_fault")
            self.set_status("The device is in FAULT state.")

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
            instance=self.Instance,
            talon_sysid_server=self.TalonDxSysIdServer,
            eth_100g_server=self.TalonDx100GEthernetServer,
            talon_status_server=self.TalonStatusServer,
            hps_master_server=self.HpsMasterServer,
            logger=self.logger,
            push_change_event_callback=self.push_change_event,
            communication_status_changed_callback=self._communication_status_changed,
            component_power_mode_changed_callback=self._component_power_mode_changed,
            component_fault_callback=self._component_fault,
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

    class OnCommand(SKABaseDevice.OnCommand):
        """
        The command class for the On command.

        Initializes HPS device proxies and starts listening to
        attribute change events
        """

        def do(self: TalonBoard.OnCommand) -> Tuple[ResultCode, str]:
            """
            Implement On command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.on()

    class OffCommand(SKABaseDevice.OffCommand):
        """
        The command class for the Off command.

        Stops listening to attribute change events
        """

        def do(self: TalonBoard.OffCommand) -> Tuple[ResultCode, str]:
            """
            Implement Off command functionality.

            :return: A Tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            component_manager = self.target
            return component_manager.off()


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(TalonBoard.main) ENABLED START #
    return run((TalonBoard,), args=args, **kwargs)
    # PROTECTED REGION END #    //  TalonBoard.main


if __name__ == "__main__":
    main()
