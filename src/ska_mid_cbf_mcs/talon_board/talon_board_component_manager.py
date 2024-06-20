# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

# Copyright (c) 2022 National Research Council of Canada

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import tango
from ska_control_model import TaskStatus
from ska_tango_base.base.base_component_manager import check_communicating
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState
from ska_tango_testing import context
from tango import AttrQuality

from ska_mid_cbf_mcs.component.component_manager import (
    CbfComponentManager,
    CommunicationStatus,
)
from ska_mid_cbf_mcs.talon_board.influxdb_query_client import (
    InfluxdbQueryClient,
)


class TalonBoardComponentManager(CbfComponentManager):
    """
    A component manager for a Talon board.
    """

    def __init__(
        self: TalonBoardComponentManager,
        *args: Any,
        hostname: str,
        influx_port: int,
        influx_org: str,
        influx_bucket: str,
        influx_auth_token: str,
        talon_sysid_address: str,
        eth_100g_address: str,
        talon_status_address: str,
        hps_master_address: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a new instance.

        :param hostname: Hostname of the Talon DX board
        :param influx_port: Influxdb port
        :param influx_org: Influxdb organization
        :param influx_bucket: Influxdb bucket to query
        :param influx_auth_token: Influxdb authentication token
        :param talon_sysid_address: Talon Sysid device server name
        :param eth_100g_address: 100g ethernet device server name (missing index suffix)
        :param talon_status_address: Talon Status device server name
        :param hps_master_address: HPS Master device server name
        """

        super().__init__(*args, **kwargs)

        # influxdb
        self._db_client = InfluxdbQueryClient(
            hostname=hostname,
            influx_port=influx_port,
            influx_org=influx_org,
            influx_bucket=influx_bucket,
            influx_auth_token=influx_auth_token,
            logger=self.logger,
        )

        # HPS device proxies.
        self._talon_sysid_fqdn = talon_sysid_address
        self._eth_100g_0_fqdn = f"{eth_100g_address}_0"
        self._eth_100g_1_fqdn = f"{eth_100g_address}_1"
        self._talon_status_fqdn = talon_status_address
        self._hps_master_fqdn = hps_master_address

        # Subscribed device proxy attributes
        self._talon_sysid_attrs = {}
        self._talon_status_attrs = {}

        self._last_check = datetime.now() - timedelta(hours=1)
        self._telemetry = dict()
        self._proxies = dict()
        self._talon_sysid_events = []
        self._talon_status_events = []

    def start_communicating(self) -> None:
        """Establish communication with the component, then start monitoring."""
        self.logger.debug(
            "Entering TalonBoardComponentManager.start_communicating"
        )

        if self.is_communicating:
            self.logger.info("Already communicating.")
            return

        super().start_communicating()
        try:
            for fqdn in [
                self._talon_sysid_fqdn,
                self._eth_100g_0_fqdn,
                self._eth_100g_1_fqdn,
                self._talon_status_fqdn,
                self._hps_master_fqdn,
            ]:
                if fqdn is not None:
                    self._proxies[fqdn] = context.DeviceProxy(device_name=fqdn)
                    self.logger.debug(f"Created device proxy for {fqdn}")
                else:
                    self._update_communication_state(
                        CommunicationStatus.NOT_ESTABLISHED
                    )
                    self.logger.error(
                        "Failed to establish proxies to devices in properties. Check charts."
                    )
                    return
        except tango.DevFailed as df:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.logger.error(df.args[0].desc)
            return

        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        # This moves the op state model.
        self._update_component_state(power=PowerState.OFF)

    def stop_communicating(self) -> None:
        """Stop communication with the component."""
        self.logger.debug(
            "Entering TalonBoardComponentManager.stop_communicating"
        )

        self._update_component_state(power=PowerState.UNKNOWN)
        # This moves the op state model.
        super().stop_communicating()

    def _subscribe_change_events(self) -> None:
        """
        Subscribe to attribute change events from HPS device proxies
        """
        # Talon System ID attributes
        self._talon_sysid_events = []

        if self._talon_sysid_fqdn is not None:
            e = {
                "version": self._proxies[
                    self._talon_sysid_fqdn
                ].add_change_event_callback(
                    attribute_name="version",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_sysid_events.append(e)
            e = {
                "Bitstream": self._proxies[
                    self._talon_sysid_fqdn
                ].add_change_event_callback(
                    attribute_name="Bitstream",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_sysid_events.append(e)

        # Talon Status attributes
        self._talon_status_events = []

        if self._talon_status_fqdn is not None:
            e = {
                "iopll_locked_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="iopll_locked_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "fs_iopll_locked_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="fs_iopll_locked_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "comms_iopll_locked_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="comms_iopll_locked_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "system_clk_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="system_clk_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "emif_bl_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="emif_bl_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "emif_br_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="emif_br_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "emif_tr_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="emif_tr_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "e100g_0_pll_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="e100g_0_pll_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "e100g_1_pll_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="e100g_1_pll_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
            e = {
                "slim_pll_fault": self._proxies[
                    self._talon_status_fqdn
                ].add_change_event_callback(
                    attribute_name="slim_pll_fault",
                    callback=self._attr_change_callback,
                    stateless=True,
                )
            }
            self._talon_status_events.append(e)
        return

    def off(self) -> tuple[ResultCode, str]:
        """
        Turn off Talon Board component;

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        :rtype: (ResultCode, str)
        """
        for ev in self._talon_sysid_events:
            for name, id in ev.items():
                self.logger.info(
                    f"Unsubscribing from event {id}, device: {self._talon_sysid_fqdn}"
                )
                self._proxies[self._talon_sysid_fqdn].remove_event(name, id)

        for ev in self._talon_status_events:
            for name, id in ev.items():
                self.logger.info(
                    f"Unsubscribing from event {id}, device: {self._talon_status_fqdn}"
                )
                self._proxies[self._talon_status_fqdn].remove_event(name, id)

        self._talon_sysid_attrs = {}
        self._talon_status_attrs = {}

        self._update_component_state(power=PowerState.OFF)
        return (ResultCode.OK, "Off completed OK")

    def _attr_change_callback(
        self, fqdn: str, name: str, value: Any, quality: AttrQuality
    ) -> None:
        if value is None:
            self.logger.warning(
                f"None value for attribute {name} of device {fqdn}"
            )
        self.logger.debug(f"Attr Change callback: {name} -> {value}")
        if fqdn == self._talon_sysid_fqdn:
            self._talon_sysid_attrs[name] = value
        elif fqdn == self._talon_status_fqdn:
            self._talon_status_attrs[name] = value
        else:
            self.logger.warning(
                f"Unexpected change callback from FQDN {fqdn}, attribute = {name}"
            )

    # ----------------------------------------------------
    # Talon board telemetry and status from device proxies
    # ----------------------------------------------------

    # The attribute change callback should get the latest values. But
    # to be safe in case the callback hasn't happened for it, do read_attribute.
    def talon_sysid_version(self) -> str:
        """Returns the bitstream version string"""
        if self._talon_sysid_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "System ID Device is not available",
                "talon_sysid_version()",
            )
        attr_name = "version"
        if attr_name not in self._talon_sysid_attrs:
            attr = self._proxies[self._talon_sysid_fqdn].read_attribute(
                attr_name
            )
            self._talon_sysid_attrs[attr_name] = attr.value
        return self._talon_sysid_attrs.get(attr_name)

    def talon_sysid_bitstream(self) -> int:
        """Returns the least 32 bits of md5 checksum of the bitstream name"""
        if self._talon_sysid_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "System ID Device is not available",
                "talon_sysid_bitstream()",
            )
        attr_name = "bitstream"
        if attr_name not in self._talon_sysid_attrs:
            attr = self._proxies[self._talon_sysid_fqdn].read_attribute(
                attr_name
            )
            self._talon_sysid_attrs[attr_name] = attr.value
        return self._talon_sysid_attrs.get(attr_name)

    def talon_status_iopll_locked_fault(self) -> bool:
        """Returns the iopll_locked_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_iopll_locked_fault()",
            )
        attr_name = "iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_fs_iopll_locked_fault(self) -> bool:
        """Returns the fs_iopll_locked_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_fs_iopll_locked_fault()",
            )
        attr_name = "fs_iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_comms_iopll_locked_fault(self) -> bool:
        """Returns the comms_iopll_locked_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_comms_iopll_locked_fault()",
            )
        attr_name = "comms_iopll_locked_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_system_clk_fault(self) -> bool:
        """Returns the system_clk_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_system_clk_fault()",
            )
        attr_name = "system_clk_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_bl_fault(self) -> bool:
        """Returns the emif_bl_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_bl_fault()",
            )
        attr_name = "emif_bl_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_br_fault(self) -> bool:
        """Returns the emif_br_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_br_fault()",
            )
        attr_name = "emif_br_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_emif_tr_fault(self) -> bool:
        """Returns the emif_tr_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_emif_tr_fault()",
            )
        attr_name = "emif_tr_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_e100g_0_pll_fault(self) -> bool:
        """Returns the e100g_0_pll_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_e100g_0_pll_fault()",
            )
        attr_name = "e100g_0_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_e100g_1_pll_fault(self) -> bool:
        """Returns the e100g_1_pll_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_e100g_1_pll_fault()",
            )
        attr_name = "e100g_1_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    def talon_status_slim_pll_fault(self) -> bool:
        """Returns the slim_pll_fault"""
        if self._talon_status_fqdn is None:
            tango.Except.throw_exception(
                "TalonBoard_NoDeviceProxy",
                "Talon Status Device is not available",
                "talon_status_slim_pll_fault()",
            )
        attr_name = "slim_pll_fault"
        if attr_name not in self._talon_status_attrs:
            attr = self._proxies[self._talon_status_fqdn].read_attribute(
                attr_name
            )
            self._talon_status_attrs[attr_name] = attr.value
        return self._talon_status_attrs.get(attr_name)

    # TODO: read attributes 100G

    # ----------------------------------------------
    # Talon board telemetry and status from Influxdb
    # ----------------------------------------------

    def fpga_die_temperature(self) -> float:
        self._throw_if_device_off()
        self._query_if_needed()
        field = "temperature-sensors_fpga-die-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def humidity_sensor_temperature(self) -> float:
        self._throw_if_device_off()
        self._query_if_needed()
        field = "temperature-sensors_humidity-temp"
        t, val = self._telemetry[field]
        self._validate_time(field, t)
        return val

    def dimm_temperatures(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 4):
            field = f"temperature-sensors_dimm-temps_{i}_temp"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_temperatures(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_temperature"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_vcc_voltages(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_vcc-3.3-voltage"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_tx_fault_status(self) -> bool:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-fault-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_tx_lol_status(self) -> bool:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-lol-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_tx_los_status(self) -> bool:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_TX_tx-los-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_rx_vcc_voltages(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_vcc-3.3-voltage"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                res.append(0)
        return res

    def mbo_rx_lol_status(self) -> bool:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_rx-lol-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def mbo_rx_los_status(self) -> bool:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        # Not all may be available.
        for i in range(0, 5):
            field = f"MBOs_{i}_RX_rx-los-status"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                res.append(False)
        return res

    def fans_pwm(self) -> list[int]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_pwm_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(int(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.warning(msg)
                res.append(-1)
        return res

    def fans_pwm_enable(self) -> list[int]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_pwm-enable_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(int(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.warning(msg)
                res.append(-1)
        return res

    def fans_fault(self) -> list[bool]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"fans_fan-fault_{i}"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(bool(val))
            else:
                msg = f"{field} cannot be read."
                self.logger.error(msg)
                res.append(-1)
        return res

    def ltm_input_voltage(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-input"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_input_voltage()",
                )
        return res

    def ltm_output_voltage_1(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-output-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_voltage_1()",
                )
        return res

    def ltm_output_voltage_2(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_voltage-output-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_voltage_2()",
                )
        return res

    def ltm_input_current(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-input"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_input_current()",
                )
        return res

    def ltm_output_current_1(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-output-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_current_1()",
                )
        return res

    def ltm_output_current_2(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_current-output-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_output_current_2()",
                )
        return res

    def ltm_temperature_1(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_temperature-1"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_temperature_1()",
                )
        return res

    def ltm_temperature_2(self) -> list[float]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            field = f"LTMs_{i}_LTM_temperature-2"
            if field in self._telemetry:
                t, val = self._telemetry[field]
                self._validate_time(field, t)
                res.append(val)
            else:
                tango.Except.throw_exception(
                    "Cannot_read_LTM_telemetry",
                    "LTM telemetries not available. This can happen if the bitstream is not programmed.",
                    "ltm_temperature_2()",
                )
        return res

    def ltm_voltage_warning(self) -> list[bool]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_voltage-output-max-alarm-1",
                f"LTMs_{i}_LTM_voltage-output-max-alarm-2",
                f"LTMs_{i}_LTM_voltage-input-crit-alarm",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res

    def ltm_current_warning(self) -> list[bool]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_current-output-max-alarm-1",
                f"LTMs_{i}_LTM_current-output-max-alarm-2",
                f"LTMs_{i}_LTM_current-input-max-alarm",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res

    def ltm_temperature_warning(self) -> list[bool]:
        self._throw_if_device_off()
        self._query_if_needed()
        res = []
        for i in range(0, 4):
            flag = False
            # Set to true for the LTM if any of the voltage alarm fields is set to 1
            fields = [
                f"LTMs_{i}_LTM_temperature-max-alarm-1",
                f"LTMs_{i}_LTM_temperature-max-alarm-2",
            ]
            for field in fields:
                if field in self._telemetry:
                    t, val = self._telemetry[field]
                    self._validate_time(field, t)
                    flag = bool(val)
                    if flag:
                        break
            res.append(flag)
        return res

    # ---------------------
    # Helper Functions
    # ---------------------

    def _throw_if_device_off(self) -> None:
        if self.power_state != PowerState.ON:
            tango.Except.throw_exception(
                "Talon_Board_Off",
                "Talon Board is OFF",
                "throw_if_device_off()",
            )
        return

    def _query_if_needed(self) -> None:
        td = datetime.now() - self._last_check
        if td.total_seconds() > 10:
            try:
                res = asyncio.run(self._db_client.do_queries())
                self._last_check = datetime.now()
                for result in res:
                    for r in result:
                        # each result is a tuple of (field, time, value)
                        self._telemetry[r[0]] = (r[1], r[2])
            except Exception as e:
                msg = f"Failed to query Influxdb of {self._db_client._hostname}: {e}"
                self.logger.error(msg)
                tango.Except.throw_exception(
                    "Query_Influxdb_Error", msg, "query_if_needed()"
                )

    def _validate_time(self, field, t) -> None:
        """
        Checks if the query result is too old. When this happens, it means
        Influxdb hasn't received a new entry in the time series recently.

        :param record: a record from Influxdb query result
        """
        td = datetime.now() - t
        if td.total_seconds() > 240:
            msg = f"Time of record {field} is too old. Currently not able to monitor device."
            self.logger.error(msg)
            tango.Except.throw_exception(
                "No new record available", msg, "validate_time()"
            )

    # ---------------------
    # Long Running Commands
    # ---------------------

    def is_on_allowed(self: TalonBoardComponentManager) -> bool:
        if self.power_state != PowerState.OFF:
            self.logger.warning(
                f"On not allowed; PowerState is {self.power_state}"
            )
            return False
        return True

    def _on(
        self: TalonBoardComponentManager,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[threading.Event] = None,
        **kwargs,
    ) -> None:
        """
        Turn on Talon Board component. This attempts to establish communication
        with the devices on the HPS, and subscribe to attribute changes.

        :raise ConnectionError: if unable to connect to HPS VCC devices
        """
        self.logger.debug("Entering TalonBoardComponentManager.on")
        task_callback(status=TaskStatus.IN_PROGRESS)

        if self.task_abort_event_is_set("On", task_callback, task_abort_event):
            return

        self._subscribe_change_events()
        self._update_component_state(power=PowerState.ON)
        ping_res = asyncio.run(self._db_client.ping())

        if not ping_res:
            self.logger.error(f"Cannot ping InfluxDB: {ping_res}")
            self._update_component_state(fault=True)
            task_callback(
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, "Failed to connect to InfluxDB"),
            )
            return

        task_callback(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "On completed OK",
            ),
        )

    @check_communicating
    def on(
        self: TalonBoardComponentManager,
        task_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> tuple[ResultCode, str]:
        self.logger.debug(f"ComponentState={self._component_state}")
        return self.submit_task(
            self._on,
            is_cmd_allowed=self.is_on_allowed,
            task_callback=task_callback,
        )
