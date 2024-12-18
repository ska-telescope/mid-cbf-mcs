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

import pytest
from assertpy import assert_that

# Tango imports
from ska_control_model import AdminMode, ResultCode
from ska_tango_testing import context
from ska_tango_testing.integration import TangoEventTracer
from tango import DevState

from ska_mid_cbf_tdc_mcs.commons.dish_utils import DISHUtils
from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes

from ... import test_utils

# Test data file path
test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestCbfController:
    """
    Test class for CbfController device class integration testing.

    As teardown and setup are expensive operations, tests are interdependent.
    This is handled by the pytest.mark.dependency decorator.

    Note: Each test needs to take in the 'controller_params' fixture to run
    instances of the suite between different parameter sets.
    """

    @pytest.mark.dependency(name="CbfController_Online")
    def test_Online(
        self: TestCbfController,
        controller: context.DeviceProxy,
        fsp: list[context.DeviceProxy],
        talon_lru: list[context.DeviceProxy],
        talon_lru_not_fitted: list[context.DeviceProxy],
        power_switch: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        subarray: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
        deployer: context.DeviceProxy,
        controller_params: dict[any],
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating.

        :param controller: The controller device proxy
        :param fsp: The list of FSP device proxies
        :param talon_lru: The list of talon_lru device proxies
        :param talon_lru_not_fitted: The list of talon_lru device proxies that are NOT_FITTED
        :param power_switch: The list of power_switch device proxies
        :param slim_fs: The slim_fs device proxy
        :param slim_vis: The slim_vis device proxy
        :param subarray: The list of subarray device proxies
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        # Generate config JSON with deployer for controller use
        deployer.targetTalons = list(
            range(1, controller_params["num_board"] + 1)
        )
        deployer.generate_config_jsons()

        # Trigger start_communicating by setting the AdminMode to ONLINE
        controller.adminMode = AdminMode.ONLINE

        expected_events = [
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.ON, DevState.DISABLE, 1),
        ]
        for device in subarray + power_switch:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # Check devices set ONLINE
        expected_events = [
            ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
            ("state", DevState.OFF, DevState.DISABLE, 1),
        ]
        for device in talon_lru + [slim_fs, slim_vis] + [controller]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # Check devices set NOT_FITTED
        expected_events = [
            ("adminMode", AdminMode.NOT_FITTED, None, 1),
        ]
        for device in talon_lru_not_fitted:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # Validate FSP function mode
        for device in fsp:
            # CIP-2550: in SimulationMode.TRUE, controller is hard-coded to only
            # set CORR function mode
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="functionMode",
                attribute_value=FspModes.CORR.value,
                previous_value=FspModes.IDLE.value,
                min_n_events=1,
            )

    @pytest.mark.dependency(
        depends=["CbfController_Online"],
        name="CbfController_InitSysParam",
    )
    def test_InitSysParam(
        self: TestCbfController,
        controller: context.DeviceProxy,
        subarray: list[context.DeviceProxy],
        vcc: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
        controller_params: dict[any],
    ) -> None:
        """
        Test the "InitSysParam" command.

        This test is dependent on the test_Online and its state changes.
        Send the InitSysParam command with the sys_param_file.

        :param controller: The controller device proxy
        :param subarray: The list of subarray device proxies
        :param vcc: The list of VCC device proxies
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        # Get the system parameters
        with open(test_data_path + controller_params["sys_param_file"]) as f:
            sys_param_str = f.read()

        # Initialize the system parameters
        result_code, command_id = controller.InitSysParam(sys_param_str)
        assert result_code == [ResultCode.QUEUED]

        # TODO: cannot check subarray/VCC dishID if sys params downloaded from CAR
        if controller_params["sys_param_from_file"]:
            for device in subarray:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name="sysParam",
                    attribute_value=sys_param_str,
                )

            dish_utils = DISHUtils(json.loads(sys_param_str))
            for vcc_id, dish_id in dish_utils.vcc_id_to_dish_id.items():
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=vcc[vcc_id - 1],
                    attribute_name="dishID",
                    attribute_value=dish_id,
                )

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

    @pytest.mark.dependency(
        depends=["CbfController_InitSysParam"],
        name="CbfController_On",
    )
    def test_On(
        self: TestCbfController,
        controller: context.DeviceProxy,
        talon_lru: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        talon_board: list[context.DeviceProxy],
        talon_board_not_fitted: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
        controller_params: dict[any],
    ):
        """
        Test the "On" command.

        This test is dependent on the test_InitSysParam and its ability
        to initialize dishIDs and SysParams. Send the On command and expect
        the controller and its subelements to transition to the ON state.

        :param controller: The controller device proxy
        :param talon_lru: The list of talon_lru device proxies
        :param slim_fs: The slim_fs device proxy
        :param slim_vis: The slim_vis device proxy
        :param talon_board: The list of talon_board device proxies
        :param talon_board_not_fitted: The list of talon_board device proxies that are NOT_FITTED
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        # Get the system parameters
        with open(test_data_path + controller_params["sys_param_file"]) as f:
            sys_param_str = f.read()

        # Send the On command
        result_code, command_id = controller.On()
        assert result_code == [ResultCode.QUEUED]

        # Validate subelements are in the correct state
        for device in talon_lru + [slim_fs, slim_vis]:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="state",
                attribute_value=DevState.ON,
                previous_value=DevState.OFF,
                min_n_events=1,
            )

        # TODO: cannot check VCC dishID if sys params downloaded from CAR
        if controller_params["sys_param_from_file"]:
            dish_utils = DISHUtils(json.loads(sys_param_str))
            for vcc_id, dish_id in dish_utils.vcc_id_to_dish_id.items():
                # TODO: indexing talon boards by VCC ID here; may need a better way
                # to grab talon IDs associated with each VCC
                board_id = vcc_id - 1

                expected_events = [
                    ("adminMode", AdminMode.ONLINE, AdminMode.OFFLINE, 1),
                    ("state", DevState.ON, DevState.DISABLE, 1),
                    ("dishID", dish_id, "", 1),
                ]
                for name, value, previous, n in expected_events:
                    assert_that(event_tracer).within_timeout(
                        test_utils.EVENT_TIMEOUT
                    ).has_change_event_occurred(
                        device_name=talon_board[board_id],
                        attribute_name=name,
                        attribute_value=value,
                        previous_value=previous,
                        min_n_events=n,
                    )

        # Check devices set NOT_FITTED
        # TODO: CIP-2550 TalonBoard devices not going to NOT_FITTED
        # expected_events = [
        #     ("adminMode", AdminMode.NOT_FITTED, None, 1),
        # ]
        # for device in talon_board_not_fitted:
        #     for name, value, previous, n in expected_events:
        #         assert_that(event_tracer).within_timeout(
        #             test_utils.EVENT_TIMEOUT
        #         ).has_change_event_occurred(
        #             device_name=device,
        #             attribute_name=name,
        #             attribute_value=value,
        #             previous_value=previous,
        #             min_n_events=n,
        #         )

        expected_events = [
            ("state", DevState.ON, DevState.OFF, 1),
            (
                "longRunningCommandResult",
                (f"{command_id[0]}", '[0, "On completed OK"]'),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=controller,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
            )

    @pytest.mark.dependency(
        depends=["CbfController_On"],
        name="CbfController_InitSysParam_NotAllowed",
    )
    def test_OnState_InitSysParam_NotAllowed(
        self: TestCbfController,
        controller: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        controller_params: dict[any],
    ):
        """
        Test that InitSysParam command is not allowed when the controller is in ON state.

        Expects the controller to already be in the ON state, and attempts to
        send the InitSysParam command.

        :param controller: The controller device proxy
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        assert controller.State() == DevState.ON

        with open(test_data_path + controller_params["sys_param_file"]) as f:
            sys_param_str = f.read()

        # Initialize the system parameters
        result_code, command_id = controller.InitSysParam(sys_param_str)
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

    @pytest.mark.dependency(
        depends=["CbfController_On"],
        name="CbfController_Off",
    )
    def test_Off(
        self,
        controller: context.DeviceProxy,
        talon_board: list[context.DeviceProxy],
        talon_lru: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        event_tracer: TangoEventTracer,
        controller_params: dict[any],
    ):
        """
        Test the "Off" command.

        This test is dependent on the test_On and its ability to turn on the controller and its subelements.
        Send the Off command and expect the controller and its subelements to transition to the expected states.

        :param controller: The controller device proxy
        :param talon_board: The list of talon_board device proxies
        :param talon_lru: The list of talon_lru device proxies
        :param slim_fs: The slim_fs device proxy
        :param slim_vis: The slim_vis device proxy
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """

        assert controller.State() == DevState.ON

        # Send the Off command
        result_code, command_id = controller.Off()
        assert result_code == [ResultCode.QUEUED]

        for device in [slim_fs, slim_vis] + talon_lru:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="state",
                attribute_value=DevState.OFF,
                previous_value=DevState.ON,
                min_n_events=1,
            )

        expected_events = [
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
            ("state", DevState.DISABLE, DevState.ON, 1),
        ]
        for device in talon_board:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        expected_events = [
            ("state", DevState.OFF, DevState.ON, 1),
            (
                "longRunningCommandResult",
                (f"{command_id[0]}", '[0, "Off completed OK"]'),
                None,
                1,
            ),
        ]
        for name, value, previous, n in expected_events:
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=controller,
                attribute_name=name,
                attribute_value=value,
                previous_value=previous,
                min_n_events=n,
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
    #     f = open(test_data_path + config_file_name)
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
    #     f = open(test_data_path + config_file_name)
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
    #     f2 = open(test_data_path + scan_file_name)
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

    @pytest.mark.dependency(
        depends=["CbfController_Off"],
        name="CbfController_Offline",
    )
    def test_Offline(
        self: TestCbfController,
        controller: context.DeviceProxy,
        fsp: list[context.DeviceProxy],
        talon_lru: list[context.DeviceProxy],
        power_switch: list[context.DeviceProxy],
        slim_fs: context.DeviceProxy,
        slim_vis: context.DeviceProxy,
        subarray: list[context.DeviceProxy],
        event_tracer: TangoEventTracer,
        controller_params: dict[any],
    ) -> None:
        """
        Verify that the component manager can stop communication.

        Set the AdminMode to OFFLINE and expect the controller and its subelements to transition to the DISABLE state.

        :param controller: The controller device proxy
        :param fsp: The list of FSP device proxies
        :param talon_lru: The list of talon_lru device proxies
        :param power_switch: The list of power_switch device proxies
        :param slim_fs: The slim_fs device proxy
        :param slim_vis: The slim_vis device proxy
        :param subarray: The list of subarray device proxies
        :param event_tracer: The event tracer for the controller
        :param controller_params: Input parameters for running different instances of the suite.
        """
        # Trigger stop_communicating by setting the AdminMode to OFFLINE
        controller.adminMode = AdminMode.OFFLINE

        # Validate FSP function mode
        for device in fsp:
            # CIP-2550: in SimulationMode.TRUE, controller is hard-coded to only
            # set CORR function mode
            assert_that(event_tracer).within_timeout(
                test_utils.EVENT_TIMEOUT
            ).has_change_event_occurred(
                device_name=device,
                attribute_name="functionMode",
                attribute_value=FspModes.IDLE.value,
                previous_value=FspModes.CORR.value,
                min_n_events=1,
            )

        expected_events = [
            ("state", DevState.DISABLE, DevState.ON, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
        ]
        for device in subarray + power_switch:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )

        # check adminMode and state changes
        expected_events = [
            ("state", DevState.DISABLE, DevState.OFF, 1),
            ("adminMode", AdminMode.OFFLINE, AdminMode.ONLINE, 1),
        ]
        for device in talon_lru + [slim_fs, slim_vis] + [controller]:
            for name, value, previous, n in expected_events:
                assert_that(event_tracer).within_timeout(
                    test_utils.EVENT_TIMEOUT
                ).has_change_event_occurred(
                    device_name=device,
                    attribute_name=name,
                    attribute_value=value,
                    previous_value=previous,
                    min_n_events=n,
                )
