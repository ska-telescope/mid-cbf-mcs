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

# TODO: config ID, scan ID, remove individual receptors, configure from ready, add receptors from ready
# TODO test fault state
# TODO: check that only used receptors are updated in delay model


class TestCbfSubarray:
    def set_Online(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Set the initial states and verify the component manager can start communicating.

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        # Trigger start_communicating by setting the AdminMode to ONLINE
        subarray[sub_id].adminMode = AdminMode.ONLINE

        expected_events = [
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.ON, DevState.DISABLE, 1),
        ]

        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(name="CbfSubarray_Setup_1")
    def test_Setup(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        controller: context.DeviceProxy,
        fsp: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Setup the initial states for subarray through turning controller ON.

        :param event_tracer: TangoEventTracer
        :param controller: proxy to controller devices
        :param fsp: dict of DeviceProxy to Fsp devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        with open(test_data_path + "sys_param_4_boards.json") as f:
            sys_param_str = f.read()

        controller.adminMode = AdminMode.ONLINE

        result_code, init_command_id = controller.InitSysParam(sys_param_str)
        assert result_code == [ResultCode.QUEUED]

        result_code, on_command_id = controller.On()
        assert result_code == [ResultCode.QUEUED]

        expected_events = [
            (
                controller,
                "longRunningCommandResult",
                (f"{init_command_id[0]}", '[0, "InitSysParam completed OK"]'),
                None,
                1,
            ),
            (controller, "state", DevState.ON, DevState.OFF, 1),
            (
                controller,
                "longRunningCommandResult",
                (f"{on_command_id[0]}", '[0, "On completed OK"]'),
                None,
                1,
            ),
            (subarray[sub_id], "state", DevState.ON, DevState.DISABLE, 1),
        ]

        for device, name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        for fsp_id in fsp:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=fsp[fsp_id],
                attribute_name="functionMode",
                attribute_value=FspModes.CORR.value,
                previous_value=FspModes.IDLE.value,
                min_n_events=1,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Setup_1"],
        name="CbfSubarray_sysParam_1",
    )
    def test_sysParam(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Test writing the sysParam attribute.

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
        ).has_change_event_occurred(
            device_name=subarray[sub_id],
            attribute_name="sysParam",
            attribute_value=sys_param_str,
            previous_value=None,
            min_n_events=1,
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
        Test CbfSubarrays's AddReceptors command.

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue AddReceptors command
        dish_ids = subarray_params["dish_ids"]
        [[result_code], [command_id]] = subarray[sub_id].AddReceptors(dish_ids)
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        expected_events = [
            ("subarrayMembership", sub_id, 0, 1),
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.ON, DevState.DISABLE, 1),
        ]
        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_AddReceptors_1"],
        name="CbfSubarray_ConfigureScan_1",
    )
    def test_ConfigureScan(
        self: TestCbfSubarray,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's ConfigureScan command.

        :param controller: DeviceProxy to CbfController device
        :param event_tracer: TangoEventTracer
        :param fsp: dict of DeviceProxy to Fsp devices
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
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
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- FSP checks --- #
        fsp_to_function_mode = {}
        for processing_region in configuration["midcbf"]["correlation"][
            "processing_regions"
        ]:
            for fsp_id in processing_region["fsp_ids"]:
                fsp_to_function_mode.update({fsp_id: FspModes.CORR})

        # TODO: Add fsp_ids that are in PST processing regions when ready

        for fsp_id, function_mode in fsp_to_function_mode.items():
            expected_events = [
                (
                    "subarrayMembership",
                    lambda e: list(e.attribute_value) == [sub_id],
                    None,
                    None,
                    1,
                ),
                ("adminMode", None, AdminMode.ONLINE, AdminMode.OFFLINE, 1),
                ("state", None, DevState.ON, DevState.DISABLE, 1),
            ]
            for name, custom, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    custom_matcher=custom,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_ConfigureScan_1"],
        name="CbfSubarray_delay_model_1",
    )
    def test_delay_model_READY(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp_corr: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        tm: context.DeviceProxy,
    ) -> None:
        """
        Test sending CbfSubarray delay model JSON in ObsState.READY.

        :param event_tracer: TangoEventTracer
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray_params: dict containing all test input parameters
        :tm: DeviceProxy to TmCspSubarrayLeafNodeTest device
        """
        # Prepare test data
        with open(test_data_path + subarray_params["delay_model_file"]) as f:
            delay_model = json.load(f)

        # Issue delay model
        tm.delayModel = json.dumps(delay_model)

        # Translate DISH IDs to VCC IDs to check FSP attribute
        dish_id_to_vcc_id = dict(
            zip(subarray_params["dish_ids"], subarray_params["vcc_ids"])
        )
        for delay_details in delay_model["receptor_delays"]:
            dish_id = delay_details["receptor"]
            if dish_id in dish_id_to_vcc_id:
                delay_details["receptor"] = dish_id_to_vcc_id[dish_id]

        # --- FSP checks --- #

        expected_events = [
            ("delayModel", json.dumps(delay_model), None, 1),
        ]
        for fsp_id in subarray_params["fsp_modes"].keys():
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

    @pytest.mark.dependency(
        depends=["CbfSubarray_delay_model_1"],
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
        Test CbfSubarrays's Scan command.

        :param event_tracer: TangoEventTracer
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
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
            ).has_change_event_occurred(
                device_name=vcc[vcc_id],
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
                previous_value=ObsState.READY,
                min_n_events=1,
            )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_modes"].keys():
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=fsp_corr[fsp_id],
                attribute_name="obsState",
                attribute_value=ObsState.SCANNING,
                previous_value=ObsState.READY,
                min_n_events=1,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Scan_1"],
        name="CbfSubarray_delay_model_2",
    )
    def test_delay_model_SCANNING(
        self: TestCbfSubarray,
        event_tracer: TangoEventTracer,
        fsp_corr: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        tm: context.DeviceProxy,
    ) -> None:
        """
        Test sending CbfSubarray delay model JSON in ObsState.SCANNING.

        :param event_tracer: TangoEventTracer
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray_params: dict containing all test input parameters
        :tm: DeviceProxy to TmCspSubarrayLeafNodeTest device
        """
        # Prepare test data
        with open(test_data_path + subarray_params["delay_model_file"]) as f:
            delay_model = json.load(f)

        # Slightly change the delay model from the one sent previously in READY
        for delay_details in delay_model["receptor_delays"]:
            new_coeff = delay_details["ypol_offset_ns"] + 1
            delay_details["ypol_offset_ns"] = new_coeff

        # Issue delay model
        tm.delayModel = json.dumps(delay_model)

        # Translate DISH IDs to VCC IDs to check FSP attribute
        dish_id_to_vcc_id = dict(
            zip(subarray_params["dish_ids"], subarray_params["vcc_ids"])
        )
        for delay_details in delay_model["receptor_delays"]:
            dish_id = delay_details["receptor"]
            if dish_id in dish_id_to_vcc_id:
                delay_details["receptor"] = dish_id_to_vcc_id[dish_id]

        # --- FSP checks --- #

        expected_events = [
            ("delayModel", json.dumps(delay_model), None, 1),
        ]
        for fsp_id in subarray_params["fsp_modes"].keys():
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
        Test CbfSubarrays's EndScan command.

        :param event_tracer: TangoEventTracer
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        # Issue EndScan command
        [[result_code], [command_id]] = subarray[sub_id].EndScan()
        assert result_code == ResultCode.QUEUED

        # --- VCC checks --- #

        for vcc_id in subarray_params["vcc_ids"]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=vcc[vcc_id],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
                previous_value=ObsState.SCANNING,
                min_n_events=1,
            )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_modes"].keys():
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=fsp_corr[fsp_id],
                attribute_name="obsState",
                attribute_value=ObsState.READY,
                previous_value=ObsState.SCANNING,
                min_n_events=1,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_ConfigureScan_1"],
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
        Test CbfSubarrays's GoToIdle command.

        :param event_tracer: TangoEventTracer
        :param fsp: dict of DeviceProxy to Fsp devices
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
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
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- FSP checks --- #

        for fsp_id, fsp_mode in subarray_params["fsp_modes"].items():
            expected_events = [
                (
                    "subarrayMembership",
                    lambda e: list(e.attribute_value) == [],
                    None,
                    None,
                    1,
                ),
                ("adminMode", None, AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", None, DevState.DISABLE, DevState.ON, 1),
            ]
            for name, custom, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    custom_matcher=custom,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

            expected_events = [
                ("obsState", ObsState.IDLE, ObsState.READY, 1),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", DevState.DISABLE, DevState.ON, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_GoToIdle_1"],
        name="CbfSubarray_ConfigureScan_validation_1",
    )
    @pytest.mark.parametrize(
        "invalid_configure_scan_file", ["ConfigureScan_AA4_values.json"]
    )
    def test_validateSupportedConfiguration(
        self: TestCbfSubarray,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        invalid_configure_scan_file: str,
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
    ) -> None:
        """
        Test setting the controller's validateSupportedConfiguration attribute
        and validate its effects on CbfSubarray ConfigureScan

        :param controller: DeviceProxy to CbfController device
        :param event_tracer: TangoEventTracer
        :param invalid_configure_scan_file: ConfigureScan input JSON that should
            fail validation
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        """
        sub_id = subarray_params["sub_id"]

        # Check the validateSupportedConfiguration is True
        assert controller.validateSupportedConfiguration is True

        # Prepare test data
        with open(test_data_path + invalid_configure_scan_file) as f:
            invalid_configuration = json.load(f)

        # Issue ConfigureScan command
        # ConfigureScan should not work here
        [[result_code], [command_id]] = subarray[sub_id].ConfigureScan(
            json.dumps(invalid_configuration)
        )
        assert result_code == ResultCode.QUEUED

        expected_events = [
            ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 1),
            ("obsState", ObsState.IDLE, ObsState.CONFIGURING, 1),
            (
                "longRunningCommandResult",
                (
                    f"{command_id}",
                    f'[{ResultCode.FAILED.value}, "Failed to validate ConfigureScan input JSON"]',
                ),
                None,
                1,
            ),
        ]

        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        controller.validateSupportedConfiguration = False
        try:
            # Issue ConfigureScan command
            # ConfigureScan should work with less restrictive checking
            [[result_code], [command_id]] = subarray[sub_id].ConfigureScan(
                json.dumps(invalid_configuration)
            )
            assert result_code == ResultCode.QUEUED

            expected_events = [
                ("obsState", ObsState.CONFIGURING, ObsState.IDLE, 2),
                ("obsState", ObsState.READY, ObsState.CONFIGURING, 1),
            ]

            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=subarray[sub_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )
        except AssertionError as ae:
            raise ae
        finally:
            controller.validateSupportedConfiguration = True

        # Issue GotoIdle command
        [[result_code], [command_id]] = subarray[sub_id].GoToIdle()
        assert result_code == ResultCode.QUEUED

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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_AddReceptors_1"],
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
        Test CbfSubarrays's RemoveAllReceptors command.

        :param event_tracer: TangoEventTracer
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
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
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Setup_1"],
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

        Set the AdminMode to OFFLINE and expect the subarray to transition to the DISABLE state.

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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfSubarray_Offline_1"],
        name="CbfSubarray_Abort_1",
    )
    def test_Abort_ObsReset(
        self: TestCbfSubarray,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's Abort and ObsReset commands

        :param controller: DeviceProxy to CbfController device
        :param event_tracer: TangoEventTracer
        :param fsp: dict of DeviceProxy to Fsp devices
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        self.set_Online(event_tracer, subarray, subarray_params)
        self.test_sysParam(event_tracer, subarray, subarray_params)

        # -------------------------
        # Abort/ObsReset from EMPTY
        # -------------------------

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [obsreset_command_id]] = subarray[sub_id].ObsReset()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events = [
            (
                "longRunningCommandResult",
                (
                    f"{abort_command_id}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            ),
            (
                "longRunningCommandResult",
                (
                    f"{obsreset_command_id}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            ),
        ]

        # ------------------------
        # Abort/ObsReset from IDLE
        # ------------------------

        self.test_AddReceptors(event_tracer, subarray, subarray_params, vcc)

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [obsreset_command_id]] = subarray[sub_id].ObsReset()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.IDLE, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{obsreset_command_id}",
                        f'[{ResultCode.OK.value}, "ObsReset completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events = [
            ("obsState", ObsState.ABORTING, ObsState.IDLE, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
        ]

        # -------------------------
        # Abort/ObsReset from READY
        # -------------------------

        self.test_ConfigureScan(
            controller,
            event_tracer,
            fsp,
            fsp_corr,
            subarray,
            subarray_params,
            vcc,
        )

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [obsreset_command_id]] = subarray[sub_id].ObsReset()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.READY, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 2),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{obsreset_command_id}",
                        f'[{ResultCode.OK.value}, "ObsReset completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.READY, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 2),
            ]
        )

        # --- FSP events --- #

        fsp_expected_events = [
            # TODO: see subarrayMembership comment above
            # ("subarrayMembership", [], [sub_id], 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]

        fsp_corr_expected_events = [
            ("obsState", ObsState.ABORTING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]

        # ----------------------------
        # Abort/ObsReset from SCANNING
        # ----------------------------

        self.test_ConfigureScan(
            controller,
            event_tracer,
            fsp,
            fsp_corr,
            subarray,
            subarray_params,
            vcc,
        )
        self.test_Scan(event_tracer, fsp_corr, subarray, subarray_params, vcc)

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [obsreset_command_id]] = subarray[sub_id].ObsReset()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 3),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 3),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 3),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{obsreset_command_id}",
                        f'[{ResultCode.OK.value}, "ObsReset completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 3),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 3),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 3),
            ]
        )

        # --- FSP events --- #

        fsp_expected_events.extend(
            [
                # TODO: see subarrayMembership comment above
                # ("subarrayMembership", [], [sub_id], 2),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 2),
                ("state", DevState.DISABLE, DevState.ON, 2),
            ]
        )

        fsp_corr_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 2),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 2),
                ("state", DevState.DISABLE, DevState.ON, 2),
            ]
        )

        # -------------------
        # Event tracer checks
        # -------------------

        # --- VCC checks --- #

        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in vcc_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_modes"].keys():
            for name, value, previous, n in fsp_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )
            for name, value, previous, n in fsp_corr_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- Subarray checks --- #

        for name, value, previous, n in subarray_expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        # --- Cleanup --- #

        self.test_RemoveAllReceptors(
            event_tracer, subarray, subarray_params, vcc
        )
        self.test_Offline(event_tracer, subarray, subarray_params)

    @pytest.mark.dependency(
        depends=["CbfSubarray_Abort_1"],
        name="CbfSubarray_Abort_2",
    )
    def test_Abort_Restart(
        self: TestCbfSubarray,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test CbfSubarrays's Abort and Restart commands

        :param controller: DeviceProxy to CbfController device
        :param event_tracer: TangoEventTracer
        :param fsp: dict of DeviceProxy to Fsp devices
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
        """
        sub_id = subarray_params["sub_id"]

        self.set_Online(event_tracer, subarray, subarray_params)
        self.test_sysParam(event_tracer, subarray, subarray_params)

        # -------------------------
        # Abort/Restart from EMPTY
        # -------------------------

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [restart_command_id]] = subarray[sub_id].Restart()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events = [
            (
                "longRunningCommandResult",
                (
                    f"{abort_command_id}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            ),
            (
                "longRunningCommandResult",
                (
                    f"{restart_command_id}",
                    f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
                ),
                None,
                1,
            ),
        ]

        # ------------------------
        # Abort/Restart from IDLE
        # ------------------------

        self.test_AddReceptors(event_tracer, subarray, subarray_params, vcc)

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [restart_command_id]] = subarray[sub_id].Restart()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.IDLE, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
                ("obsState", ObsState.RESTARTING, ObsState.ABORTED, 1),
                ("obsState", ObsState.EMPTY, ObsState.RESTARTING, 1),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{restart_command_id}",
                        f'[{ResultCode.OK.value}, "Restart completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events = [
            ("obsState", ObsState.ABORTING, ObsState.IDLE, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
            ("subarrayMembership", 0, sub_id, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]

        # -------------------------
        # Abort/Restart from READY
        # -------------------------

        self.test_AddReceptors(event_tracer, subarray, subarray_params, vcc)
        self.test_ConfigureScan(
            controller,
            event_tracer,
            fsp,
            fsp_corr,
            subarray,
            subarray_params,
            vcc,
        )

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [restart_command_id]] = subarray[sub_id].Restart()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.READY, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESTARTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.EMPTY, ObsState.RESTARTING, 2),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{restart_command_id}",
                        f'[{ResultCode.OK.value}, "Restart completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.READY, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 2),
                ("subarrayMembership", 0, sub_id, 2),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 2),
                ("state", DevState.DISABLE, DevState.ON, 2),
            ]
        )

        # --- FSP events --- #

        fsp_expected_events = [
            # TODO: see subarrayMembership comment above
            # ("subarrayMembership", [], [sub_id], 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]

        fsp_corr_expected_events = [
            ("obsState", ObsState.ABORTING, ObsState.READY, 1),
            ("obsState", ObsState.ABORTED, ObsState.ABORTING, 1),
            ("obsState", ObsState.RESETTING, ObsState.ABORTED, 1),
            ("obsState", ObsState.IDLE, ObsState.RESETTING, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]

        # ----------------------------
        # Abort/Restart from SCANNING
        # ----------------------------

        self.test_AddReceptors(event_tracer, subarray, subarray_params, vcc)
        self.test_ConfigureScan(
            controller,
            event_tracer,
            fsp,
            fsp_corr,
            subarray,
            subarray_params,
            vcc,
        )
        self.test_Scan(event_tracer, fsp_corr, subarray, subarray_params, vcc)

        [[result_code], [abort_command_id]] = subarray[sub_id].Abort()
        assert result_code == ResultCode.QUEUED

        [[result_code], [restart_command_id]] = subarray[sub_id].Restart()
        assert result_code == ResultCode.QUEUED

        # --- Subarray events --- #

        subarray_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 3),
                ("obsState", ObsState.RESTARTING, ObsState.ABORTED, 3),
                ("obsState", ObsState.EMPTY, ObsState.RESTARTING, 3),
                (
                    "longRunningCommandResult",
                    (
                        f"{abort_command_id}",
                        f'[{ResultCode.OK.value}, "Abort completed OK"]',
                    ),
                    None,
                    1,
                ),
                (
                    "longRunningCommandResult",
                    (
                        f"{restart_command_id}",
                        f'[{ResultCode.OK.value}, "Restart completed OK"]',
                    ),
                    None,
                    1,
                ),
            ]
        )

        # --- VCC events --- #

        vcc_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 3),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 3),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 3),
                ("subarrayMembership", 0, sub_id, 3),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 3),
                ("state", DevState.DISABLE, DevState.ON, 3),
            ]
        )

        # --- FSP events --- #

        fsp_expected_events.extend(
            [
                # TODO: see subarrayMembership comment above
                # ("subarrayMembership", [], [sub_id], 2),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 2),
                ("state", DevState.DISABLE, DevState.ON, 2),
            ]
        )

        fsp_corr_expected_events.extend(
            [
                ("obsState", ObsState.ABORTING, ObsState.SCANNING, 1),
                ("obsState", ObsState.ABORTED, ObsState.ABORTING, 2),
                ("obsState", ObsState.RESETTING, ObsState.ABORTED, 2),
                ("obsState", ObsState.IDLE, ObsState.RESETTING, 2),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 2),
                ("state", DevState.DISABLE, DevState.ON, 2),
            ]
        )

        # -------------------
        # Event tracer checks
        # -------------------

        # --- VCC checks --- #

        for vcc_id in subarray_params["vcc_ids"]:
            for name, value, previous, n in vcc_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- FSP checks --- #

        for fsp_id in subarray_params["fsp_modes"].keys():
            for name, value, previous, n in fsp_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )
            for name, value, previous, n in fsp_corr_expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- Subarray checks --- #

        for name, value, previous, n in subarray_expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        # --- Cleanup --- #

        self.test_Offline(event_tracer, subarray, subarray_params)

    @pytest.mark.dependency(
        depends=["CbfSubarray_Offline_1"],
        name="CbfSubarray_Reconfigure_1",
    )
    def test_ConfigureScan_from_ready(
        self: TestCbfSubarray,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        fsp: dict[int, context.DeviceProxy],
        fsp_corr: dict[int, context.DeviceProxy],
        subarray: dict[int, context.DeviceProxy],
        subarray_params: dict[any],
        vcc: dict[int, context.DeviceProxy],
    ) -> None:
        """
        Test re-configuring CbfSubarray from READY

        :param controller: DeviceProxy to CbfController device
        :param event_tracer: TangoEventTracer
        :param fsp: dict of DeviceProxy to Fsp devices
        :param fsp_corr: dict of DeviceProxy to FspCorrSubarray devices
        :param subarray: list of proxies to subarray devices
        :param subarray_params: dict containing all test input parameters
        :param vcc: dict of DeviceProxy to Vcc devices
        """
        if "alt_params" not in subarray_params:
            pytest.skip("No alternate configuration provided.")

        alt_params = subarray_params["alt_params"]
        sub_id = subarray_params["sub_id"]

        self.set_Online(event_tracer, subarray, subarray_params)
        self.test_sysParam(event_tracer, subarray, subarray_params)
        self.test_AddReceptors(event_tracer, subarray, subarray_params, vcc)
        self.test_ConfigureScan(
            controller,
            event_tracer,
            fsp,
            fsp_corr,
            subarray,
            subarray_params,
            vcc,
        )

        # ------------------------
        # ConfigureScan from READY
        # ------------------------

        # Prepare test data
        with open(test_data_path + alt_params["configure_scan_file"]) as f:
            alt_configuration = json.load(f)

        # Issue ConfigureScan command
        [[result_code], [command_id]] = subarray[sub_id].ConfigureScan(
            json.dumps(alt_configuration)
        )
        assert result_code == ResultCode.QUEUED

        # -------------------
        # Event tracer checks
        # -------------------

        # --- FSP checks --- #

        # First we check the original FSPs are IDLE
        for fsp_id, fsp_mode in subarray_params["fsp_modes"].items():
            expected_events = [
                (
                    "subarrayMembership",
                    lambda e: list(e.attribute_value) == [],
                    None,
                    None,
                    1,
                ),
                ("adminMode", None, AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", None, DevState.DISABLE, DevState.ON, 1),
            ]
            for name, custom, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    custom_matcher=custom,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

            expected_events = [
                ("obsState", ObsState.IDLE, ObsState.READY, 1),
                ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
                ("state", DevState.DISABLE, DevState.ON, 1),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # Now we check the new FSPs are READY
        for fsp_id, fsp_mode in alt_params["fsp_modes"].items():
            expected_events = [
                (
                    "subarrayMembership",
                    lambda e: list(e.attribute_value) == [sub_id],
                    None,
                    None,
                    1,
                ),
                ("adminMode", None, AdminMode.ONLINE, AdminMode.OFFLINE, 1),
                ("state", None, DevState.ON, DevState.DISABLE, 1),
            ]
            for name, custom, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=fsp[fsp_id],
                    custom_matcher=custom,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
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
                ).has_change_event_occurred(
                    device_name=fsp_corr[fsp_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- VCC events --- #

        # Assigned VCCs will be the same when configuring from READY
        for vcc_id in alt_params["vcc_ids"]:
            expected_events = [
                (
                    "frequencyBand",
                    alt_params["freq_band"],
                    subarray_params["freq_band"],
                    1,
                ),
                ("obsState", ObsState.CONFIGURING, ObsState.READY, 1),
                ("obsState", ObsState.READY, ObsState.CONFIGURING, 2),
            ]
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id],
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # --- Subarray checks --- #

        expected_events = [
            ("obsState", ObsState.CONFIGURING, ObsState.READY, 1),
            ("obsState", ObsState.READY, ObsState.CONFIGURING, 2),
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
            ).has_change_event_occurred(
                device_name=subarray[sub_id],
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

        # --- Cleanup --- #
        self.test_GoToIdle(
            event_tracer, fsp, fsp_corr, subarray, subarray_params, vcc
        )
        self.test_RemoveAllReceptors(
            event_tracer, subarray, subarray_params, vcc
        )
        self.test_Offline(event_tracer, subarray, subarray_params)
