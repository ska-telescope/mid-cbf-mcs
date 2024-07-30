#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

from __future__ import annotations

import json
import os

from assertpy import assert_that

# Tango imports
from ska_control_model import AdminMode, ObsState, ResultCode

# Tango imports
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_mcs.commons.dish_utils import DISHUtils

from ... import test_utils

data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestCbfController:
    """
    Test class for CbfController device class integration testing.
    """

    def test_Online(
        self: TestCbfController,
        controller: context.DeviceProxy,
        all_sub_devices: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating
        """

        # trigger start_communicating by setting the AdminMode to ONLINE
        controller.adminMode = AdminMode.ONLINE

        # check adminMode and state changes
        for device in [controller] + all_sub_devices:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="adminMode",
                attribute_value=AdminMode.ONLINE,
            )

            # PowerSwitch device starts up in ON state when turned ONLINE
            if "mid_csp_cbf/power_switch/" in device.dev_name():
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name="state",
                    attribute_value=DevState.ON,
                )
            else:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name="state",
                    attribute_value=DevState.OFF,
                )

    def test_InitSysParam(
        self: TestCbfController,
        controller: context.DeviceProxy,
        vcc: list[context.DeviceProxy],
        talon_board: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Test the "InitSysParam" command
        """
        # Get the system parameters
        data_file_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
        )
        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        dish_utils = DISHUtils(json.loads(sp))

        # Initialize the system parameters
        result_code, command_id = controller.InitSysParam(sp)
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.OK.value}, "InitSysParam completed OK"]',
            ),
        )

        for vcc_id, dish_id in dish_utils.vcc_id_to_dish_id.items():
            event_tracer.subscribe_event(vcc[vcc_id - 1], "dishID")
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=vcc[vcc_id - 1],
                attribute_name="dishID",
                attribute_value=dish_id,
            )

            # TODO: indexing talon boards by VCC ID here; may need a better way
            # to grab talon IDs associated with each VCC
            event_tracer.subscribe_event(talon_board[vcc_id - 1], "dishID")
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=talon_board[vcc_id - 1],
                attribute_name="dishID",
                attribute_value=dish_id,
            )

    def test_On(
        self: TestCbfController,
        controller: context.DeviceProxy,
        powered_sub_devices: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
    ):
        """
        Test the "On" command
        """
        # Send the On command
        result_code, command_id = controller.On()
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="state",
            attribute_value=DevState.ON,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="longRunningCommandResult",
            attribute_value=(f"{command_id[0]}", '[0, "On completed OK"]'),
        )

        # Validate subelements are in the correct state
        for device in powered_sub_devices:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="state",
                attribute_value=DevState.ON,
            )

    def test_OnState_InitSysParam_NotAllowed(
        self: TestCbfController,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
    ):
        """
        Test that InitSysParam command is not allowed when the controller is in ON state
        """
        assert controller.State() == DevState.ON

        # Get the system parameters
        data_file_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
        )
        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()

        # Initialize the system parameters
        result_code, command_id = controller.InitSysParam(sp)
        assert result_code == [ResultCode.QUEUED]

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="longRunningCommandResult",
            attribute_value=(
                f"{command_id[0]}",
                f'[{ResultCode.NOT_ALLOWED.value}, "Command is not allowed"]',
            ),
        )

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "source_init_sys_param.json",
            "source_init_sys_param_retrieve_from_car.json",
        ],
    )
    def test_SourceInitSysParam(
        self, subdevices_under_test, config_file_name: str
    ):
        """
        Test that InitSysParam file can be retrieved from CAR
        """
        if subdevices_under_test.controller.State() == DevState.ON:
            subdevices_under_test.controller.Off()
        with open(data_file_path + config_file_name) as f:
            sp = f.read()
        result = subdevices_under_test.controller.InitSysParam(sp)

        assert subdevices_under_test.controller.State() == DevState.OFF
        assert result[0] == ResultCode.OK
        assert subdevices_under_test.controller.sourceSysParam == sp
        sp_json = json.loads(sp)
        tm_data_sources = sp_json["tm_data_sources"][0]
        tm_data_filepath = sp_json["tm_data_filepath"]
        retrieved_init_sys_param_file = TMData([tm_data_sources])[
            tm_data_filepath
        ].get_dict()
        assert subdevices_under_test.controller.sysParam == json.dumps(
            retrieved_init_sys_param_file
        )

    def test_Off(
        self,
        controller: context.DeviceProxy,
        talon_board: list[context.DeviceProxy],
        talon_lru: list[context.DeviceProxy],
        subarray: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        fsp: list[context.DeviceProxy],
        vcc: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
    ):
        """
        Test the "Off" command
        """

        assert controller.State() == DevState.ON

        # Send the Off command
        result_code, command_id = controller.Off()
        assert result_code == [ResultCode.QUEUED]

        for device in subarray:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="obsState",
                attribute_value=ObsState.EMPTY,
            )

        for device in (
            [slim_fs, slim_vis]
            + vcc
            + fsp
            + subarray
            + talon_board
            + talon_lru
        ):
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="state",
                attribute_value=DevState.OFF,
            )
            if "mid_csp_cbf/vcc" in device:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name="obsState",
                    attribute_value=ObsState.IDLE,
                )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="state",
            attribute_value=DevState.OFF,
        )

        assert_that(event_tracer).within_timeout(
            test_utils.EVENT_TIMEOUT
        ).has_change_event_occurred(
            device_name=controller,
            attribute_name="longRunningCommandResult",
            attribute_value=(f"{command_id[0]}", '[0, "Off completed OK"]'),
        )

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_controller.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Off_GoToIdle_RemoveAllReceptors(
    #     self, subdevices_under_test, config_file_name, receptors, vcc_receptors
    # ):
    #     """
    #     Test the "Off" command resetting the subelement observing state machines.
    #     """

    #     wait_time_s = 5
    #     sleep_time_s = 0.1

    #     # turn system on
    #     self.test_On(subdevices_under_test)

    #     # load scan config
    #     f = open(data_file_path + config_file_name)
    #     json_string = f.read().replace("\n", "")
    #     f.close()
    #     configuration = json.loads(json_string)

    #     sub_id = int(configuration["common"]["subarray_id"])

    #     # Off from IDLE to test RemoveAllReceptors path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    #     # turn system on
    #     self.test_On(subdevices_under_test)

    #     # Off from READY to test GoToIdle path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # configure scan
    #     subdevices_under_test.subarray[sub_id].ConfigureScan(json_string)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.READY,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    # @pytest.mark.parametrize(
    #     "config_file_name, \
    #     scan_file_name, \
    #     receptors, \
    #     vcc_receptors",
    #     [
    #         (
    #             "ConfigureScan_controller.json",
    #             "Scan1_basic.json",
    #             ["SKA001", "SKA036", "SKA063", "SKA100"],
    #             [4, 1],
    #         )
    #     ],
    # )
    # def test_Off_Abort(
    #     self,
    #     subdevices_under_test,
    #     config_file_name,
    #     scan_file_name,
    #     receptors,
    #     vcc_receptors,
    # ):
    #     """
    #     Test the "Off" command resetting the subelement observing state machines.
    #     """
    #     wait_time_s = 5
    #     sleep_time_s = 1

    #     self.test_On(subdevices_under_test)

    #     # load scan config
    #     f = open(data_file_path + config_file_name)
    #     json_string = f.read().replace("\n", "")
    #     f.close()
    #     configuration = json.loads(json_string)
    #     sub_id = int(configuration["common"]["subarray_id"])

    #     # Off from SCANNING to test Abort path
    #     # add receptors
    #     subdevices_under_test.subarray[sub_id].AddReceptors(receptors)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.IDLE,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # configure scan
    #     subdevices_under_test.subarray[sub_id].ConfigureScan(json_string)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.READY,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Scan command
    #     f2 = open(data_file_path + scan_file_name)
    #     json_string_scan = f2.read().replace("\n", "")
    #     f2.close()
    #     subdevices_under_test.subarray[sub_id].Scan(json_string_scan)
    #     subdevices_under_test.wait_timeout_obs(
    #         [subdevices_under_test.subarray[sub_id]],
    #         ObsState.SCANNING,
    #         wait_time_s,
    #         sleep_time_s,
    #     )

    #     # send the Off command
    #     subdevices_under_test.controller.Off()
    #     subdevices_under_test.wait_timeout_dev(
    #         [subdevices_under_test.controller], DevState.OFF, wait_time_s, sleep_time_s
    #     )

    def test_Offline(
        self: TestCbfController,
        controller: context.DeviceProxy,
        sub_devices: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
    ) -> None:
        """
        Verify the component manager can stop communicating
        """
        # Trigger stop_communicating by setting the AdminMode to OFFLINE
        controller.adminMode = AdminMode.OFFLINE

        # check adminMode and state changes
        for device in [controller] + sub_devices:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="adminMode",
                attribute_value=AdminMode.OFFLINE,
            )
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="state",
                attribute_value=DevState.DISABLE,
            )
