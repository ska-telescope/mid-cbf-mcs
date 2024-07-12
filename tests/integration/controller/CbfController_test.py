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

import json
import os
import socket

import pytest

# Tango imports
from ska_control_model import LoggingLevel, SimulationMode
from ska_tango_base.base.base_device import (
    _DEBUGGER_PORT,  # DeviceStateModel, removed in v0.11.3
)
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import AdminMode, ObsState
from ska_telmodel.data import TMData
from tango import DevState

# Standard imports


# Local imports

data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


@pytest.mark.usefixtures("test_proxies")
class TestCbfController:
    """
    Test class for CbfController device class integration testing.
    """

    @pytest.mark.skip(reason="enable to test DebugDevice")
    def test_DebugDevice(self, device_under_test):
        port = device_under_test.DebugDevice()
        assert port == _DEBUGGER_PORT
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", _DEBUGGER_PORT))
        device_under_test.On()

    def test_Connect(
        self, device_under_test, test_proxies, change_event_callbacks
    ):
        """
        Test the initial states and verify the component manager
        can start communicating
        """
        # After init devices should be in DISABLE state, but just in case...
        device_under_test.adminMode = AdminMode.OFFLINE
        assert device_under_test.State() == DevState.DISABLE
        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.subarray[i].adminMode = AdminMode.OFFLINE
            assert test_proxies.subarray[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.vcc[i].adminMode = AdminMode.OFFLINE
            assert test_proxies.vcc[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.fsp[i].adminMode = AdminMode.OFFLINE
            assert test_proxies.fsp[i].State() == DevState.DISABLE
        # for mesh in test_proxies.slim:
        #     mesh.adminMode = AdminMode.OFFLINE
        #     assert mesh.State() == DevState.DISABLE
        # for i in ["CORR", "PSS-BF", "PST-BF"]:
        #     for j in range(1, test_proxies.num_sub + 1):
        #         for k in range(1, test_proxies.num_fsp + 1):
        #             test_proxies.fspSubarray[i][j][k].adminMode = AdminMode.OFFLINE
        #             assert (
        #                 test_proxies.fspSubarray[i][j][k].State()
        #                 == DevState.DISABLE
        #             )

        device_under_test.simulationMode = SimulationMode.TRUE
        device_under_test.loggingLevel = LoggingLevel.DEBUG

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE
        change_event_callbacks["State"].assert_change_event(DevState.OFF)

    def test_On(self, device_under_test, test_proxies, change_event_callbacks):
        """
        Test the "On" command
        """
        # Get the system parameters
        data_file_path = (
            os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
        )
        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()

        # Initialize the system parameters
        device_under_test.InitSysParam(sp)

        # Send the On command
        device_under_test.On()

        # After ON devices should be in ONLINE state
        change_event_callbacks["State"].assert_change_event(DevState.ON)
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].adminMode == AdminMode.ONLINE
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].adminMode == AdminMode.ONLINE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].adminMode == AdminMode.ONLINE
        for mesh in test_proxies.slim:
            assert mesh.adminMode == AdminMode.ONLINE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[i][j][k].adminMode
                        == AdminMode.ONLINE
                    )

    # TODO: Update tests below.

    def test_InitSysParam_Condition(self, test_proxies):
        """
        Test that InitSysParam can only be used when
        the controller op state is OFF
        """
        if test_proxies.controller.State() == DevState.OFF:
            test_proxies.controller.On()
        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        result = test_proxies.controller.InitSysParam(sp)
        assert result[0] == ResultCode.FAILED

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "source_init_sys_param.json",
            "source_init_sys_param_retrieve_from_car.json",
        ],
    )
    def test_SourceInitSysParam(self, test_proxies, config_file_name: str):
        """
        Test that InitSysParam file can be retrieved from CAR
        """
        if test_proxies.controller.State() == DevState.ON:
            test_proxies.controller.Off()
        with open(data_file_path + config_file_name) as f:
            sp = f.read()
        result = test_proxies.controller.InitSysParam(sp)

        assert test_proxies.controller.State() == DevState.OFF
        assert result[0] == ResultCode.OK
        assert test_proxies.controller.sourceSysParam == sp
        sp_json = json.loads(sp)
        tm_data_sources = sp_json["tm_data_sources"][0]
        tm_data_filepath = sp_json["tm_data_filepath"]
        retrieved_init_sys_param_file = TMData([tm_data_sources])[
            tm_data_filepath
        ].get_dict()
        assert test_proxies.controller.sysParam == json.dumps(
            retrieved_init_sys_param_file
        )

    def test_Off(self, test_proxies):
        """
        Test the "Off" command
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # if controller is already off, we must turn it On before turning off.
        if test_proxies.controller.State() == DevState.OFF:
            test_proxies.controller.On()
            test_proxies.wait_timeout_dev(
                [test_proxies.controller],
                DevState.ON,
                wait_time_s,
                sleep_time_s,
            )

        assert test_proxies.controller.State() == DevState.ON
        # send the Off command
        test_proxies.controller.Off()

        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert test_proxies.controller.State() == DevState.OFF

        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.subarray[i]],
                DevState.OFF,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert test_proxies.vcc[i].State() == DevState.OFF

        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert test_proxies.fsp[i].State() == DevState.OFF

        for mesh in test_proxies.slim:
            test_proxies.wait_timeout_dev(
                [mesh], DevState.OFF, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.OFF

        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    test_proxies.wait_timeout_dev(
                        [test_proxies.fspSubarray[i][j][k]],
                        DevState.OFF,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.OFF
                    )

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_controller.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            )
        ],
    )
    def test_Off_GoToIdle_RemoveAllReceptors(
        self, test_proxies, config_file_name, receptors, vcc_receptors
    ):
        """
        Test the "Off" command resetting the subelement observing state machines.
        """

        wait_time_s = 5
        sleep_time_s = 0.1

        # turn system on
        self.test_On(test_proxies)

        # load scan config
        f = open(data_file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_string)

        sub_id = int(configuration["common"]["subarray_id"])

        # Off from IDLE to test RemoveAllReceptors path
        # add receptors
        test_proxies.subarray[sub_id].AddReceptors(receptors)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.IDLE,
            wait_time_s,
            sleep_time_s,
        )

        # send the Off command
        test_proxies.controller.Off()
        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )

        assert test_proxies.controller.State() == DevState.OFF
        # subelements should be in observing state EMPTY (subarray) or IDLE (VCC/FSP)
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF
            assert test_proxies.subarray[i].obsState == ObsState.EMPTY
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF
            assert test_proxies.vcc[i].obsState == ObsState.IDLE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for mesh in test_proxies.slim:
            assert mesh.State() == DevState.OFF
        for func in ["CORR", "PSS-BF", "PST-BF"]:
            for sub in range(1, test_proxies.num_sub + 1):
                for fsp in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].State()
                        == DevState.OFF
                    )
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].obsState
                        == ObsState.IDLE
                    )

        # turn system on
        self.test_On(test_proxies)

        # Off from READY to test GoToIdle path
        # add receptors
        test_proxies.subarray[sub_id].AddReceptors(receptors)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.IDLE,
            wait_time_s,
            sleep_time_s,
        )

        # configure scan
        test_proxies.subarray[sub_id].ConfigureScan(json_string)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )

        # send the Off command
        test_proxies.controller.Off()
        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )

        assert test_proxies.controller.State() == DevState.OFF
        # subelements should be in observing state EMPTY (subarray) or IDLE (VCC/FSP)
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF
            assert test_proxies.subarray[i].obsState == ObsState.EMPTY
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF
            assert test_proxies.vcc[i].obsState == ObsState.IDLE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for mesh in test_proxies.slim:
            assert mesh.State() == DevState.OFF
        for func in ["CORR", "PSS-BF", "PST-BF"]:
            for sub in range(1, test_proxies.num_sub + 1):
                for fsp in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].State()
                        == DevState.OFF
                    )
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].obsState
                        == ObsState.IDLE
                    )

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_controller.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            )
        ],
    )
    def test_Off_Abort(
        self,
        test_proxies,
        config_file_name,
        scan_file_name,
        receptors,
        vcc_receptors,
    ):
        """
        Test the "Off" command resetting the subelement observing state machines.
        """
        wait_time_s = 5
        sleep_time_s = 1

        self.test_On(test_proxies)

        # load scan config
        f = open(data_file_path + config_file_name)
        json_string = f.read().replace("\n", "")
        f.close()
        configuration = json.loads(json_string)
        sub_id = int(configuration["common"]["subarray_id"])

        # Off from SCANNING to test Abort path
        # add receptors
        test_proxies.subarray[sub_id].AddReceptors(receptors)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.IDLE,
            wait_time_s,
            sleep_time_s,
        )

        # configure scan
        test_proxies.subarray[sub_id].ConfigureScan(json_string)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.READY,
            wait_time_s,
            sleep_time_s,
        )

        # send the Scan command
        f2 = open(data_file_path + scan_file_name)
        json_string_scan = f2.read().replace("\n", "")
        f2.close()
        test_proxies.subarray[sub_id].Scan(json_string_scan)
        test_proxies.wait_timeout_obs(
            [test_proxies.subarray[sub_id]],
            ObsState.SCANNING,
            wait_time_s,
            sleep_time_s,
        )

        # send the Off command
        test_proxies.controller.Off()
        test_proxies.wait_timeout_dev(
            [test_proxies.controller], DevState.OFF, wait_time_s, sleep_time_s
        )

        assert test_proxies.controller.State() == DevState.OFF
        # subelements should be in observing state EMPTY (subarray) or IDLE (VCC/FSP)
        for i in range(1, test_proxies.num_sub + 1):
            assert test_proxies.subarray[i].State() == DevState.OFF
            assert test_proxies.subarray[i].obsState == ObsState.EMPTY
        for i in range(1, test_proxies.num_vcc + 1):
            assert test_proxies.vcc[i].State() == DevState.OFF
            assert test_proxies.vcc[i].obsState == ObsState.IDLE
        for i in range(1, test_proxies.num_fsp + 1):
            assert test_proxies.fsp[i].State() == DevState.OFF
        for mesh in test_proxies.slim:
            assert mesh.State() == DevState.OFF
        for func in ["CORR", "PSS-BF", "PST-BF"]:
            for sub in range(1, test_proxies.num_sub + 1):
                for fsp in range(1, test_proxies.num_fsp + 1):
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].State()
                        == DevState.OFF
                    )
                    assert (
                        test_proxies.fspSubarray[func][sub][fsp].obsState
                        == ObsState.IDLE
                    )

    def test_Standby(self, test_proxies):
        """
        Test the "Standby" command
        """
        wait_time_s = 3
        sleep_time_s = 0.1

        # send the Standby command
        test_proxies.controller.Standby()

        test_proxies.wait_timeout_dev(
            [test_proxies.controller],
            DevState.STANDBY,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.controller.State() == DevState.STANDBY

        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]],
                DevState.STANDBY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.vcc[i].State() == DevState.STANDBY

        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]],
                DevState.STANDBY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.fsp[i].State() == DevState.STANDBY

    def test_Disconnect(self, test_proxies):
        """
        Verify the component manager can stop communicating
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        # trigger stop_communicating by setting the AdminMode to OFFLINE
        test_proxies.controller.adminMode = AdminMode.OFFLINE

        # controller device should be in DISABLE state after stop_communicating
        test_proxies.wait_timeout_dev(
            [test_proxies.controller],
            DevState.DISABLE,
            wait_time_s,
            sleep_time_s,
        )
        assert test_proxies.controller.State() == DevState.DISABLE
        for i in range(1, test_proxies.num_sub + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.subarray[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_vcc + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.vcc[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.vcc[i].State() == DevState.DISABLE
        for i in range(1, test_proxies.num_fsp + 1):
            test_proxies.wait_timeout_dev(
                [test_proxies.fsp[i]],
                DevState.DISABLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.fsp[i].State() == DevState.DISABLE
        for mesh in test_proxies.slim:
            test_proxies.wait_timeout_dev(
                [mesh], DevState.DISABLE, wait_time_s, sleep_time_s
            )
            assert mesh.State() == DevState.DISABLE
        for i in ["CORR", "PSS-BF", "PST-BF"]:
            for j in range(1, test_proxies.num_sub + 1):
                for k in range(1, test_proxies.num_fsp + 1):
                    test_proxies.wait_timeout_dev(
                        [test_proxies.fspSubarray[i][j][k]],
                        DevState.DISABLE,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.fspSubarray[i][j][k].State()
                        == DevState.DISABLE
                    )
