#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""
from __future__ import annotations  # allow forward references in type hints

import json
import os

import pytest
from assertpy import assert_that
from ska_control_model import AdminMode, ObsState, ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import FspModes, freq_band_dict

from ... import test_utils

# Test data file path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# TODO: previous attr value, num values, config ID, scan ID, delay models


class TestCbfSubarray:
    @pytest.mark.dependency(name="CbfSubarray_Online_1")
    def test_Online(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        # trigger start_communicating by setting the AdminMode to ONLINE
        subarray[sub_id].adminMode = AdminMode.ONLINE

        expected_events = [
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.ON, DevState.DISABLE, 1),
        ]

        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Online_1"],
        name="CbfSubarray_sysParam_1",
    )
    def test_sysParam(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Test writing the sysParam attribute

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        with open(test_data_path + subarray_params["sys_param_file"]) as f:
            sys_param_str = f.read()

        subarray[sub_id].sysParam = sys_param_str

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).cbf_has_change_event_occurred(
            device_name=subarray[sub_id],
            attribute_name="sysParam",
            attribute_value=sys_param_str,
            previous_value=None,
            target_n_events=1,
        )

    @pytest.mark.dependency(
        depends=["CbfSubarray_sysParam_1"],
        name="CbfSubarray_AddReceptors_1",
    )
    def test_AddReceptors(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's AddReceptors command

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue AddReceptors command
        dish_ids = subarray_params["dish_ids"]
        [[result_code], [command_id]] = subarray[sub_id].AddReceptors(dish_ids)
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        expected_events = [
            ("subarrayMembership", subarray_params["sub_id"], 0, 1),
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.ON, DevState.DISABLE, 1),
        ]
        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- Subarray checks --- #

        expected_events = [
            ("receptors", tuple(dish_ids), (), 1),
            ("obsState", ObsState.RESOURCING, ObsState.EMPTY, 1),
            ("obsState", ObsState.IDLE, ObsState.RESOURCING, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "AddReceptors completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_AddReceptors_1"],
        name="CbfSubarray_ConfigureScan_1",
    )
    def test_ConfigureScan(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's ConfigureScan command

        :param event_tracer: TangoEventTracer
        :fsp: dict of DeviceProxy to Fsp devices
        :fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Prepare test data
        with open(
            test_data_path + subarray_params["configure_scan_file"]
        ) as f:
            configuration = json.load(f)

        # Issue ConfigureScan command
        [[result_code], [command_id]] = subarray[sub_id].ConfigureScan(
            json.dumps(configuration)
        )
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        frequency_band = freq_band_dict()[
            configuration["common"]["frequency_band"]
        ]["band_index"]

        expected_events = [
            ("frequencyBand", frequency_band, None, 1),
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
        ]
        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- FSP checks --- #

        for fsp_config in configuration["cbf"]["fsp"]:
            fsp_id = fsp_config["fsp_id"]
            function_mode = FspModes[fsp_config["function_mode"]].value

            expected_events = [
                ("subarrayMembership", [sub_id], None, 1),
                ("functionMode", function_mode, FspModes.IDLE.value, 1),
                ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
                ("state", DevState.ON, DevState.DISABLE, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

            expected_events = [
                ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
                ("state", DevState.ON, DevState.DISABLE, 1),
                ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
                ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- Subarray checks --- #

        expected_events = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "ConfigureScan completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_ConfigureScan_1"],
        name="CbfSubarray_Scan_1",
    )
    def test_Scan(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's Scan command

        :param event_tracer: TangoEventTracer
        :fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Prepare test data
        with open(test_data_path + subarray_params["scan_file"]) as f:
            scan = json.load(f)

        # Issue Scan command
        [[result_code], [command_id]] = subarray[sub_id].Scan(json.dumps(scan))
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        for vcc_id in subarray_params["vcc_ids"]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=vcc[vcc_id],
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
                previous_value=ObsState.READY,
                target_n_events=1,
            )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_ids"]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=fsp_corr[fsp_id],
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
                previous_value=ObsState.READY,
                target_n_events=1,
            )

        # --- Subarray checks --- #

        expected_events = [
            ("obsState", ObsState.SCANNING, ObsState.READY, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "Scan completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Scan_1"],
        name="CbfSubarray_EndScan_1",
    )
    def test_EndScan(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's EndScan command

        :param event_tracer: TangoEventTracer
        :fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue EndScan command
        [[result_code], [command_id]] = subarray[sub_id].EndScan()
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        for vcc_id in subarray_params["vcc_ids"]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=vcc[vcc_id],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
                previous_value=ObsState.SCANNING,
                target_n_events=1,
            )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_ids"]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=fsp_corr[fsp_id],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
                previous_value=ObsState.SCANNING,
                target_n_events=1,
            )

        # --- Subarray checks --- #

        expected_events = [
            ("obsState", ObsState.READY, ObsState.SCANNING, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "EndScan completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_EndScan_1"],
        name="CbfSubarray_GoToIdle_1",
    )
    def test_GoToIdle(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's EndScan command

        :param event_tracer: TangoEventTracer
        :fsp: dict of DeviceProxy to Fsp devices
        :fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue GoToIdle command
        [[result_code], [command_id]] = subarray[sub_id].GoToIdle()
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        expected_events = [
            ("frequencyBand", 0, None, 1),
            ("obsState", ObsState.IDLE, ObsState.READY, 1),
        ]
        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_ids"]:
            expected_events = [
                # TODO: this check fails, even though an event is received; test logs below
                # ReceivedEvent(device_name='mid_csp_cbf/fsp/01', attribute_name='subarraymembership', attribute_value=[], reception_time=2024-08-06 19:12:45.976597)
                # TANGO_TRACER Query arguments: device_name='mid_csp_cbf/fsp/01', attribute_name='subarrayMembership', attribute_value=[],
                # Query start time: 2024-08-06 19:12:46.064362
                # Query end time: 2024-08-06 19:13:46.065521
                # ("subarrayMembership", [], [sub_id], 1),
                ("functionMode", FspModes.IDLE.value, None, 1),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", DevState.DISABLE, DevState.ON, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

            expected_events = [
                ("obsState", ObsState.IDLE, ObsState.READY, 1),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", DevState.DISABLE, DevState.ON, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- Subarray checks --- #

        expected_events = [
            ("obsState", ObsState.IDLE, ObsState.READY, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "GoToIdle completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_GoToIdle_1"],
        name="CbfSubarray_RemoveAllReceptors_1",
    )
    def test_RemoveAllReceptors(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's EndScan command

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue RemoveAllReceptors command
        [[result_code], [command_id]] = subarray[sub_id].RemoveAllReceptors()
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        expected_events = [
            ("subarrayMembership", 0, sub_id, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]
        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).cbf_has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    target_n_events=n,
                )

        # --- Subarray checks --- #

        expected_events = [
            ("receptors", (), tuple(subarray_params["dish_ids"]), 1),
            ("obsState", ObsState.RESOURCING, ObsState.IDLE, 1),
            ("obsState", ObsState.EMPTY, ObsState.RESOURCING, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.OK.value}, "RemoveAllReceptors completed OK"]',
                ),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_RemoveAllReceptors_1"],
        name="CbfSubarray_Offline_1",
    )
    def test_Offline(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Verify component manager can stop communication with the component.

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        subarray[sub_id].adminMode = AdminMode.OFFLINE

        expected_events = [
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).cbf_has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                target_n_events=n,
            )

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Scan_Twice_Same_Config(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Scan command running twice on the same scan configuration.

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])
    #         test_proxies.on()
    #         time.sleep(sleep_time_s)
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # send the EndScan command
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         # send the Scan command again
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         scan_configuration = json.loads(json_string_scan)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         scan_id = scan_configuration["scan_id"]

    #         # check scanID on VCC and FSP
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][fsp_id].scanID
    #                     == scan_id
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].scanID
    #                     == scan_id
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].scanID
    #                     == scan_id
    #                 )
    #         for r in vcc_ids:
    #             assert test_proxies.vcc[r].scanID == scan_id

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
    #         for r in vcc_ids:
    #             assert test_proxies.vcc[r].obsState == ObsState.SCANNING
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )

    #         # clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].End()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "config_1_file_name, \
    #     config_2_file_name, \
    #     scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Scan_Twice_Different_Configs(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     config_1_file_name: str,
    #     config_2_file_name: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Scan command running twice on different scan configurations.

    #     :param proxies: proxies pytest fixture
    #     :param config_1_file_name: JSON file for the first configuration
    #     :param config_2_file_name: JSON file for the second configuration
    #     :param scan_file: JSON file for both scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         # get the first configuration
    #         f = open(test_data_path + config_1_file_name)
    #         json_1_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration_1 = json.loads(json_1_string)
    #         sub_id = int(configuration_1["common"]["subarray_id"])

    #         # get the second configuration
    #         f = open(test_data_path + config_2_file_name)
    #         json_2_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration_2 = json.loads(json_2_string)
    #         assert sub_id == int(configuration_2["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # configure first scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_1_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         # send first Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # send the EndScan command
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         # configure second scan
    #         test_proxies.subarray[sub_id].ConfigureScan(json_2_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         # check configured attributes of CBF subarray
    #         assert (
    #             test_proxies.subarray[sub_id].configurationID
    #             == configuration_2["common"]["config_id"]
    #         )
    #         band_index = freq_band_dict()[
    #             configuration_2["common"]["frequency_band"]
    #         ]["band_index"]
    #         assert band_index == test_proxies.subarray[sub_id].frequencyBand
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY

    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check the rest of the configured attributes of VCCs
    #         for r in vcc_ids:
    #             assert test_proxies.vcc[r].frequencyBand == band_index
    #             assert test_proxies.vcc[r].subarrayMembership == sub_id
    #             assert (
    #                 test_proxies.vcc[r].configID
    #                 == configuration_2["common"]["config_id"]
    #             )
    #             if "band_5_tuning" in configuration_2["common"]:
    #                 for idx, band in enumerate(
    #                     configuration_2["common"]["band_5_tuning"]
    #                 ):
    #                     assert test_proxies.vcc[r].band5Tuning[idx] == band
    #             if "frequency_band_offset_stream1" in configuration_2["cbf"]:
    #                 assert (
    #                     test_proxies.vcc[r].frequencyBandOffsetStream1
    #                     == configuration_2["cbf"][
    #                         "frequency_band_offset_stream1"
    #                     ]
    #                 )
    #             if "frequency_band_offset_stream2" in configuration_2["cbf"]:
    #                 assert (
    #                     test_proxies.vcc[r].frequencyBandOffsetStream2
    #                     == configuration_2["cbf"][
    #                         "frequency_band_offset_stream2"
    #                     ]
    #                 )
    #             if "rfi_flagging_mask" in configuration_2["cbf"]:
    #                 assert test_proxies.vcc[r].rfiFlaggingMask == str(
    #                     configuration_2["cbf"]["rfi_flagging_mask"]
    #                 )

    #         time.sleep(1)
    #         # check configured attributes of VCC search windows
    #         if "search_window" in configuration_2["cbf"]:
    #             for idx, search_window in enumerate(
    #                 configuration_2["cbf"]["search_window"]
    #             ):
    #                 for r in vcc_ids:
    #                     assert (
    #                         test_proxies.vccSw[r][idx + 1].tdcEnable
    #                         == search_window["tdc_enable"]
    #                     )
    #                     # TODO implement VCC SW functionality and
    #                     # correct power states
    #                     if search_window["tdc_enable"]:
    #                         assert (
    #                             test_proxies.vccSw[r][idx + 1].State()
    #                             == DevState.DISABLE
    #                         )
    #                     else:
    #                         assert (
    #                             test_proxies.vccSw[r][idx + 1].State()
    #                             == DevState.DISABLE
    #                         )
    #                     assert (
    #                         test_proxies.vccSw[r][idx + 1].searchWindowTuning
    #                         == search_window["search_window_tuning"]
    #                     )
    #                     if "tdc_num_bits" in search_window:
    #                         assert (
    #                             test_proxies.vccSw[r][idx + 1].tdcNumBits
    #                             == search_window["tdc_num_bits"]
    #                         )
    #                     if "tdc_period_before_epoch" in search_window:
    #                         assert (
    #                             test_proxies.vccSw[r][
    #                                 idx + 1
    #                             ].tdcPeriodBeforeEpoch
    #                             == search_window["tdc_period_before_epoch"]
    #                         )
    #                     if "tdc_period_after_epoch" in search_window:
    #                         assert (
    #                             test_proxies.vccSw[r][
    #                                 idx + 1
    #                             ].tdcPeriodAfterEpoch
    #                             == search_window["tdc_period_after_epoch"]
    #                         )
    #                     if "tdc_destination_address" in search_window:
    #                         for t in search_window["tdc_destination_address"]:
    #                             if (
    #                                 test_proxies.dish_utils.dish_id_to_vcc_id[
    #                                     t["receptor_id"]
    #                                 ]
    #                                 == r
    #                             ):
    #                                 tdcDestAddr = t["tdc_destination_address"]
    #                                 assert (
    #                                     list(
    #                                         test_proxies.vccSw[r][
    #                                             idx + 1
    #                                         ].tdcDestinationAddress
    #                                     )
    #                                     == tdcDestAddr
    #                                 )

    #         # check configured attributes of FSPs, including states of function mode capabilities
    #         for fsp in configuration_2["cbf"]["fsp"]:
    #             fsp_id = fsp["fsp_id"]
    #             logging.info("Check for fsp id = {}".format(fsp_id))

    #             if fsp["function_mode"] == "CORR":
    #                 function_mode = FspModes.CORR.value
    #                 assert (
    #                     test_proxies.fsp[fsp_id].functionMode == function_mode
    #                 )
    #                 assert (
    #                     sub_id in test_proxies.fsp[fsp_id].subarrayMembership
    #                 )
    #                 # check configured attributes of FSP subarray
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #                 # If receptors are not specified, then
    #                 # all the subarray receptors are used
    #                 receptorsSpecified = False
    #                 if "receptors" in fsp:
    #                     if fsp["receptors"] != []:
    #                         receptorsSpecified = True

    #                 fsp_corr_assigned_vcc = list(
    #                     test_proxies.fspSubarray["CORR"][sub_id][fsp_id].vccIDs
    #                 )

    #                 if receptorsSpecified:
    #                     config_fsp_corr_vcc = [
    #                         test_proxies.dish_utils.dish_id_to_vcc_id[r]
    #                         for r in fsp["receptors"]
    #                     ]
    #                 else:
    #                     config_fsp_corr_vcc = [
    #                         test_proxies.dish_utils.dish_id_to_vcc_id[r]
    #                         for r in receptors
    #                     ]

    #                 assert sorted(fsp_corr_assigned_vcc) == sorted(
    #                     config_fsp_corr_vcc
    #                 )

    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].frequencyBand
    #                     == band_index
    #                 )
    #                 if "band_5_tuning" in configuration_2["common"]:
    #                     for idx, band in enumerate(
    #                         configuration_2["common"]["band_5_tuning"]
    #                     ):
    #                         assert (
    #                             test_proxies.fspSubarray["CORR"][sub_id][
    #                                 fsp_id
    #                             ].band5Tuning[idx]
    #                             == band
    #                         )
    #                 if (
    #                     "frequency_band_offset_stream1"
    #                     in configuration_2["cbf"]
    #                 ):
    #                     assert (
    #                         test_proxies.fspSubarray["CORR"][sub_id][
    #                             fsp_id
    #                         ].frequencyBandOffsetStream1
    #                         == configuration_2["cbf"][
    #                             "frequency_band_offset_stream1"
    #                         ]
    #                     )
    #                 if (
    #                     "frequency_band_offset_stream2"
    #                     in configuration_2["cbf"]
    #                 ):
    #                     assert (
    #                         test_proxies.fspSubarray["CORR"][sub_id][
    #                             fsp_id
    #                         ].frequencyBandOffsetStream2
    #                         == configuration_2["cbf"][
    #                             "frequency_band_offset_stream2"
    #                         ]
    #                     )
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].frequencySliceID
    #                     == fsp["frequency_slice_id"]
    #                 )
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].integrationFactor
    #                     == fsp["integration_factor"]
    #                 )
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].corrBandwidth
    #                     == fsp["zoom_factor"]
    #                 )
    #                 if fsp["zoom_factor"] > 0:
    #                     assert (
    #                         test_proxies.fspSubarray["CORR"][sub_id][
    #                             fsp_id
    #                         ].zoomWindowTuning
    #                         == fsp["zoom_window_tuning"]
    #                     )
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].fspChannelOffset
    #                     == fsp["channel_offset"]
    #                 )

    #                 if "channel_averaging_map" in fsp:
    #                     for i in range(len(fsp["channel_averaging_map"])):
    #                         for j in range(
    #                             len(fsp["channel_averaging_map"][i])
    #                         ):
    #                             assert (
    #                                 test_proxies.fspSubarray["CORR"][sub_id][
    #                                     fsp_id
    #                                 ].channelAveragingMap[i][j]
    #                                 == fsp["channel_averaging_map"][i][j]
    #                             )

    #                 if "output_link_map" in fsp:
    #                     for i in range(len(fsp["output_link_map"])):
    #                         for j in range(len(fsp["output_link_map"][i])):
    #                             assert (
    #                                 test_proxies.fspSubarray["CORR"][sub_id][
    #                                     fsp_id
    #                                 ].outputLinkMap[i][j]
    #                                 == fsp["output_link_map"][i][j]
    #                             )

    #             elif fsp["function_mode"] == "PSS-BF":
    #                 function_mode = FspModes.PSS_BF.value
    #                 assert (
    #                     test_proxies.fsp[fsp_id].functionMode == function_mode
    #                 )
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].searchWindowID
    #                     == fsp["search_window_id"]
    #                 )

    #                 # TODO: currently searchBeams is stored by the device
    #                 #       as a json string ( via attribute 'searchBeams');
    #                 #       this has to be updated in FspPssSubarray
    #                 #       to read/write individual members
    #                 for idx, sBeam in enumerate(
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].searchBeams
    #                 ):
    #                     # TODO: bug in FSP seems that searchBeams not cleared
    #                     #  from previous scan configs even after deconfigure
    #                     searchBeam = json.loads(sBeam)
    #                     assert (
    #                         searchBeam["search_beam_id"]
    #                         == fsp["search_beam"][idx]["search_beam_id"]
    #                     )
    #                     # TODO currently only one receptor supported
    #                     assert (
    #                         searchBeam["receptor_ids"][0]
    #                         == test_proxies.dish_utils.dish_id_to_vcc_id[
    #                             fsp["search_beam"][idx]["receptor_ids"][0]
    #                         ]
    #                     )
    #                     assert (
    #                         searchBeam["enable_output"]
    #                         == fsp["search_beam"][idx]["enable_output"]
    #                     )
    #                     assert (
    #                         searchBeam["averaging_interval"]
    #                         == fsp["search_beam"][idx]["averaging_interval"]
    #                     )
    #                     # TODO - this does not pass - to debug & fix
    #                     # assert searchBeam["searchBeamDestinationAddress"] == fsp["search_beam"][idx]["search_beam_destination_address"]

    #             elif fsp["function_mode"] == "PST-BF":
    #                 function_mode = FspModes.PST_BF.value
    #                 assert (
    #                     test_proxies.fsp[fsp_id].functionMode == function_mode
    #                 )

    #                 assert test_proxies.fsp[fsp_id].State() == DevState.ON
    #                 assert (
    #                     sub_id in test_proxies.fsp[fsp_id].subarrayMembership
    #                 )

    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #                 for beam in fsp["timing_beam"]:
    #                     # TODO currently only one receptor supported
    #                     assert (
    #                         test_proxies.fspSubarray["PST-BF"][sub_id][
    #                             fsp_id
    #                         ].vccIDs[0]
    #                         == test_proxies.dish_utils.dish_id_to_vcc_id[
    #                             beam["receptor_ids"][0]
    #                         ]
    #                     )

    #                     assert all(
    #                         [
    #                             test_proxies.fspSubarray["PST-BF"][sub_id][
    #                                 fsp_id
    #                             ].timingBeamID[i]
    #                             == j
    #                             for i, j in zip(
    #                                 range(1), [beam["timing_beam_id"]]
    #                             )
    #                         ]
    #                     )

    #             elif fsp["function_mode"] == "VLBI":
    #                 function_mode = FspModes.VLBI.value
    #                 assert (
    #                     test_proxies.fsp[fsp_id].functionMode == function_mode
    #                 )
    #                 # TODO: This mode is not tested yet

    #         # send second Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         scan_configuration = json.loads(json_string_scan)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         scan_id = scan_configuration["scan_id"]

    #         # check scanID on VCC and FSP
    #         for fsp in configuration_2["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][fsp_id].scanID
    #                     == scan_id
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].scanID
    #                     == scan_id
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].scanID
    #                     == scan_id
    #                 )
    #         for r in vcc_ids:
    #             assert test_proxies.vcc[r].scanID == scan_id

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
    #         for r in vcc_ids:
    #             assert test_proxies.vcc[r].obsState == ObsState.SCANNING
    #         for fsp in configuration_2["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.SCANNING
    #                 )

    #         # clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].End()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.off()
    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA036", "SKA063", "SKA001", "SKA100"],
    #             [4, 1],
    #         ),
    #     ],
    # )
    # def test_Abort_Reset(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Abort and ObsReset commands

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # -------------------- #
    #         # abort from READY #
    #         # -------------------- #
    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert sorted(
    #             list(test_proxies.subarray[sub_id].receptors)
    #         ) == sorted(receptors)
    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.READY
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.READY

    #         # abort
    #         test_proxies.subarray[sub_id].Abort()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.ABORTED,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.ABORTED
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.ABORTED

    #         # ObsReset
    #         test_proxies.subarray[sub_id].ObsReset()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
    #         assert sorted(
    #             list(test_proxies.subarray[sub_id].receptors)
    #         ) == sorted(receptors)
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         # ------------------- #
    #         # abort from SCANNING #
    #         # ------------------- #
    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert sorted(
    #             list(test_proxies.subarray[sub_id].receptors)
    #         ) == sorted(receptors)
    #         # configure scan
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         # scan
    #         f = open(test_data_path + scan_file)
    #         json_string_scan = f.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f.close()
    #         scan_configuration = json.loads(json_string_scan)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
    #         assert (
    #             test_proxies.subarray[sub_id].scanID
    #             == scan_configuration["scan_id"]
    #         )
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.SCANNING
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING

    #         # abort
    #         test_proxies.subarray[sub_id].Abort()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.ABORTED,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.ABORTED
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.ABORTED

    #         # ObsReset
    #         test_proxies.subarray[sub_id].ObsReset()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
    #         assert test_proxies.subarray[sub_id].scanID == 0
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             "Scan2_basic.json",
    #             ["SKA036", "SKA063", "SKA001", "SKA100"],
    #             [4, 1],
    #         ),
    #     ],
    # )
    # def test_Abort_Restart(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Abort and Restart commands

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # --------------- #
    #         # abort from IDLE #
    #         # --------------- #
    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
    #         # abort
    #         test_proxies.subarray[sub_id].Abort()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.ABORTED,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

    #         # At this point in the test, we only need to assert that the VCCs
    #         # are aborted and not the FSPs, as the FSPs are not added to
    #         # their respective group_proxy until ConfigureScan is executed.
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.ABORTED

    #         # Restart: receptors should be empty
    #         test_proxies.subarray[sub_id].Restart()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
    #         assert len(test_proxies.subarray[sub_id].receptors) == 0

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         # ---------------- #
    #         # abort from READY #
    #         # ---------------- #
    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.READY
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.READY

    #         # abort
    #         test_proxies.subarray[sub_id].Abort()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.ABORTED,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.ABORTED
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.ABORTED

    #         # Restart
    #         test_proxies.subarray[sub_id].Restart()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
    #         assert len(test_proxies.subarray[sub_id].receptors) == 0

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         # ------------------- #
    #         # abort from SCANNING #
    #         # ------------------- #
    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )
    #         # scan
    #         f = open(test_data_path + scan_file)
    #         json_string_scan = f.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f.close()
    #         scan_configuration = json.loads(json_string_scan)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
    #         assert (
    #             test_proxies.subarray[sub_id].scanID
    #             == scan_configuration["scan_id"]
    #         )
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.SCANNING
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.SCANNING

    #         # abort
    #         test_proxies.subarray[sub_id].Abort()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.ABORTED,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.ABORTED
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.ABORTED

    #         # Restart
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].Restart()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert len(test_proxies.subarray[sub_id].receptors) == 0
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # # TODO: remove entirely?
    # @pytest.mark.skip(
    #     reason="OffCommand will not be invoked in this manner by CSP LMC Mid, \
    #     rather a series of commands will be issued (Abort -> Restart/Reset)"
    # )
    # def test_Abort_from_Resourcing(self, test_proxies):
    #     """
    #     Test CbfSubarrays's Abort command from ObsState.RESOURCING.

    #     :param test_proxies: proxies pytest fixture
    #     """
    #     try:
    #         pass

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             ["SKA036", "SKA063", "SKA001", "SKA100"],
    #             [4, 1],
    #         ),
    #     ],
    # )
    # def test_Fault_Restart(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Restart from ObsState.FAULT

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 3
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

    #         # send invalid configuration to trigger fault state
    #         # note that invalid config will trigger exception, ignore it
    #         with pytest.raises(Exception):
    #             test_proxies.subarray[sub_id].ConfigureScan("INVALID JSON")
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.FAULT,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.FAULT

    #         # Restart
    #         test_proxies.subarray[sub_id].Restart()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert len(test_proxies.subarray[sub_id].receptors) == 0
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     receptors, \
    #     vcc_ids",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         ),
    #         (
    #             "ConfigureScan_CORR_PSS_PST.json",
    #             ["SKA036", "SKA063", "SKA001", "SKA100"],
    #             [4, 1],
    #         ),
    #     ],
    # )
    # def test_Fault_ObsReset(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     receptors: list[str],
    #     vcc_ids: list[int],
    # ) -> None:
    #     """
    #     Test CbfSubarrays's Obsreset from ObsState.FAULT

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_ids: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 3
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

    #         # send invalid configuration to trigger fault state
    #         # note that invalid config will trigger exception, ignore it
    #         with pytest.raises(Exception):
    #             test_proxies.subarray[sub_id].ConfigureScan("INVALID JSON")
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.FAULT,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.FAULT

    #         # ObsReset
    #         test_proxies.subarray[sub_id].ObsReset()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
    #         assert sorted(
    #             list(test_proxies.subarray[sub_id].receptors)
    #         ) == sorted(receptors)
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             assert (
    #                 test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
    #                     fsp_id
    #                 ].obsState
    #                 == ObsState.IDLE
    #             )
    #         for vcc_id in vcc_ids:
    #             assert test_proxies.vcc[vcc_id].obsState == ObsState.IDLE

    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     receptors_to_remove, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_remove_receptors_in_the_middle_of_scan(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     receptors_to_remove: list[int],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test removing receptors in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param receptors_to_remove: list of ids of receptors to remove
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attempt to remove receptors
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].RemoveReceptors(
    #                 receptors_to_remove
    #             )

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     receptors_to_remove, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_remove_all_receptors_in_the_middle_of_scan(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     receptors_to_remove: list[int],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test removing all receptors in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param receptors_to_remove: list of ids of receptors to remove
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attempt to remove all receptors
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].RemoveAllReceptors()

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_add_receptors_in_the_middle_of_scan(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test adding receptors in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attemp to add receptors
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].AddReceptors(receptors)

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # @pytest.mark.skip(reason="Currently fails, CIP-2308")
    # def test_call_off_cmd_in_the_middle_of_scan(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test calling off command in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attemp to call off command
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].Off()

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_configure_scan_in_the_middle_of_scanning(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test configuring the scan in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attemp to configure scan

    #         with pytest.raises(
    #             DevFailed,
    #             match="Action configure_invoked is not allowed in obs state SCANNING.",
    #         ):
    #             test_proxies.subarray[sub_id].ConfigureScan(json_string)

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_go_to_idle_in_the_middle_of_scanning(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test go to idle in the middle of a scan to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # send the Scan command
    #         f2 = open(test_data_path + scan_file)
    #         json_string_scan = f2.read().replace("\n", "")
    #         test_proxies.subarray[sub_id].Scan(json_string_scan)
    #         f2.close()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.SCANNING,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         # check states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

    #         # attempt to go to idle
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].GoToIdle()

    #         # Clean up
    #         wait_time_s = 3
    #         test_proxies.subarray[sub_id].EndScan()
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e

    # @pytest.mark.parametrize(
    #     "configure_scan_file, \
    #     scan_file, \
    #     receptors, \
    #     receptors_to_remove, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_basic_CORR.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_add_receptors_in_ready_state(
    #     self: TestCbfSubarray,
    #     test_proxies: pytest.fixture,
    #     configure_scan_file: str,
    #     scan_file: str,
    #     receptors: list[str],
    #     receptors_to_remove: list[int],
    #     vcc_receptors: list[int],
    # ) -> None:
    #     """
    #     Test adding receptors in Ready state to confirm graceful failure

    #     :param proxies: proxies pytest fixture
    #     :param configure_scan_file: JSON file for the configuration
    #     :param scan_file: JSON file for the scan configuration
    #     :param receptors: list of receptor ids
    #     :param receptors_to_remove: list of ids of receptors to remove
    #     :param vcc_receptors: list of vcc receptor ids
    #     """
    #     try:
    #         wait_time_s = 1
    #         sleep_time_s = 1

    #         f = open(test_data_path + configure_scan_file)
    #         json_string = f.read().replace("\n", "")
    #         f.close()
    #         configuration = json.loads(json_string)

    #         sub_id = int(configuration["common"]["subarray_id"])

    #         test_proxies.on()
    #         time.sleep(sleep_time_s)

    #         assert test_proxies.subarray[sub_id].State() == DevState.ON
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

    #         # add receptors
    #         test_proxies.subarray[sub_id].AddReceptors(receptors)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         assert all(
    #             [
    #                 test_proxies.subarray[sub_id].receptors[i] == j
    #                 for i, j in zip(range(len(receptors)), receptors)
    #             ]
    #         )

    #         # configure scan
    #         wait_time_configure = 5
    #         test_proxies.subarray[sub_id].ConfigureScan(json_string)
    #         test_proxies.wait_timeout_obs(
    #             [test_proxies.subarray[sub_id]],
    #             ObsState.READY,
    #             wait_time_configure,
    #             sleep_time_s,
    #         )

    #         # check initial states
    #         assert test_proxies.subarray[sub_id].obsState == ObsState.READY
    #         for r in vcc_receptors:
    #             assert test_proxies.vcc[r].obsState == ObsState.READY
    #         for fsp in configuration["cbf"]["fsp"]:
    #             fsp_id = int(fsp["fsp_id"])
    #             if fsp["function_mode"] == "CORR":
    #                 assert (
    #                     test_proxies.fspSubarray["CORR"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PSS-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PSS-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )
    #             elif fsp["function_mode"] == "PST-BF":
    #                 assert (
    #                     test_proxies.fspSubarray["PST-BF"][sub_id][
    #                         fsp_id
    #                     ].obsState
    #                     == ObsState.READY
    #                 )

    #         # attempt to add receptors
    #         with pytest.raises(
    #             DevFailed, match="Command not permitted by state model."
    #         ):
    #             test_proxies.subarray[sub_id].AddReceptors(receptors)

    #         # clean up
    #         test_proxies.subarray[sub_id].GoToIdle()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.IDLE,
    #             wait_time_s,
    #             sleep_time_s,
    #         )
    #         test_proxies.subarray[sub_id].RemoveAllReceptors()
    #         test_proxies.wait_timeout_obs(
    #             [
    #                 test_proxies.vcc[i]
    #                 for i in range(1, test_proxies.num_vcc + 1)
    #             ],
    #             ObsState.EMPTY,
    #             wait_time_s,
    #             sleep_time_s,
    #         )

    #         test_proxies.off()

    #     except AssertionError as ae:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise ae
    #     except Exception as e:
    #         time.sleep(2)
    #         test_proxies.clean_test_proxies()
    #         time.sleep(2)
    #         raise e
