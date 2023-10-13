#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-prototype project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""
from __future__ import annotations  # allow forward references in type hints

import copy
import json
import logging
import os
import random

# Standard imports
import time
from typing import List

import pytest
from ska_tango_base.control_model import AdminMode, ObsState
from tango import DevState

from ska_mid_cbf_mcs.commons.global_enum import FspModes, freq_band_dict
from ska_mid_cbf_mcs.commons.receptor_utils import ReceptorUtils

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


# Tango imports

# SKA specific imports


class TestCbfSubarray:
    @pytest.mark.parametrize("sub_id", [1])
    def test_Connect(
        self: TestCbfSubarray, test_proxies: pytest.fixture, sub_id: int
    ) -> None:
        """
        Test the initial states and verify the component manager
        can start communicating

        :param test_proxies: the proxies test fixture
        :param sub_id: the subarray id
        """

        wait_time_s = 3
        sleep_time_s = 0.1

        device_under_test = test_proxies.subarray[sub_id]

        assert device_under_test.State() == DevState.DISABLE

        # trigger start_communicating by setting the AdminMode to ONLINE
        device_under_test.adminMode = AdminMode.ONLINE

        # subarray device should be in ON state after start_communicating
        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize("sub_id", [1])
    def test_On_Off(
        self: TestCbfSubarray, test_proxies: pytest.fixture, sub_id: int
    ) -> None:
        """
        Test the "On" command

        :param test_proxies: the proxies test fixture
        :param sub_id: the subarray id
        """
        wait_time_s = 3
        sleep_time_s = 1

        device_under_test = test_proxies.subarray[sub_id]

        with open(data_file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        device_under_test.sysParam = sp

        sys_param = json.loads(sp)
        test_proxies.receptor_utils = ReceptorUtils(sys_param)

        device_under_test.On()

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.ON, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()

        test_proxies.wait_timeout_dev(
            [device_under_test], DevState.OFF, wait_time_s, sleep_time_s
        )
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize(
        "receptors, \
        receptors_to_remove, \
        sub_id",
        [
            (
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                ["SKA100", "SKA001", "SKA063"],
                1,
            ),
            (["SKA063", "SKA001", "SKA100"], ["SKA100", "SKA001"], 1),
        ],
    )
    def test_AddRemoveReceptors_valid(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        receptors: List[str],
        receptors_to_remove: List[int],
        sub_id: int,
    ) -> None:
        """
        Test CbfSubarrays's AddReceptors and RemoveReceptors commands

        :param proxies: proxies pytest fixture
        :param receptors: list of receptor ids
        :param receptors_to_remove: list of ids of receptors to remove
        :param sub_id: the subarray id
        """

        if test_proxies.debug_device_is_on:
            test_proxies.subarray[sub_id].DebugDevice()

        try:
            wait_time_s = 3
            sleep_time_s = 1

            # controller will turn On/Off all of its subordinate devices,
            # including the subarrays, FSPs and VCCs
            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all(
                [
                    test_proxies.vcc[i].subarrayMembership == 0
                    for i in range(1, test_proxies.num_vcc + 1)
                ]
            )

            # add all except last receptor
            test_proxies.subarray[sub_id].AddReceptors(receptors[:-1])
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )

            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors[:-1]))
            ] == receptors[:-1]

            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == sub_id
                    for r in receptors[:-1]
                ]
            )

            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # add the last receptor
            test_proxies.subarray[sub_id].AddReceptors([receptors[-1]])
            time.sleep(1)
            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors))
            ] == receptors
            assert (
                test_proxies.vcc[
                    test_proxies.receptor_utils.receptor_id_to_vcc_id[receptors[-1]]
                ].subarrayMembership
                == sub_id
            )

            # remove all except last receptor
            test_proxies.subarray[sub_id].RemoveReceptors(receptors_to_remove)
            time.sleep(1)
            receptors_after_remove = [
                r for r in receptors if r not in receptors_to_remove
            ]
            for idx, receptor in enumerate(receptors_after_remove):
                assert test_proxies.subarray[sub_id].receptors[idx] == receptor
                assert (
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[receptor]
                    ].subarrayMembership
                    == sub_id
                )
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == 0
                    for r in receptors_to_remove
                ]
            )

            # remove remaining receptor
            test_proxies.subarray[sub_id].RemoveReceptors(
                receptors_after_remove
            )
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            for receptor in receptors_after_remove:
                assert (
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[receptor]
                    ].subarrayMembership
                    == 0
                )
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptor_id, \
        sub_id",
        [
            (["SKA001", "SKA036"], ["SKA200"], 1),
            (["SKA063", "SKA100"], ["0"], 1),
        ],
    )
    def test_AddReceptors_invalid_single(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        receptors: List[str],
        invalid_receptor_id: List[int],
        sub_id: int,
    ) -> None:
        """
        Test CbfSubarrays's AddReceptors command for a single subarray
            when the receptor id is invalid

        :param proxies: proxies pytest fixture
        :param receptors: list of receptor ids
        :param invalid_receptor_id: invalid receptor id
        :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all(
                [
                    test_proxies.vcc[i].subarrayMembership == 0
                    for i in range(1, test_proxies.num_vcc + 1)
                ]
            )

            # add some receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors))
            ] == receptors
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == 1
                    for r in receptors
                ]
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try adding an invalid receptor ID
            # Validation of input receptors will throw an
            # exception if there is an invalid receptor id
            with pytest.raises(Exception):
                test_proxies.subarray[sub_id].AddReceptors(invalid_receptor_id)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors))
            ] == receptors
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == 1
                    for r in receptors
                ]
            )

            test_proxies.subarray[sub_id].RemoveAllReceptors()

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            test_proxies.clean_test_proxies()
            raise e

    @pytest.mark.parametrize(
        "receptors, \
        invalid_receptors_to_remove, \
        sub_id",
        [
            (["SKA001", "SKA036"], ["SKA100"], 1),
            (["SKA063", "SKA100"], ["SKA001", "SKA036"], 1),
        ],
    )
    def test_RemoveReceptors_invalid_single(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        receptors: List[str],
        invalid_receptors_to_remove: List[int],
        sub_id: int,
    ) -> None:
        """
        Test CbfSubarrays's RemoveReceptors command for a single subarray:
            - when a receptor id is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray

        :param proxies: proxies pytest fixture
        :param receptors: list of receptor ids
        :param invalid_receptors_to_remove: invalid receptor ids
        :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all(
                [
                    test_proxies.vcc[i].subarrayMembership == 0
                    for i in range(1, test_proxies.num_vcc + 1)
                ]
            )

            # add some receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors))
            ] == receptors
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == 1
                    for r in receptors
                ]
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try removing a receptor not assigned to subarray 1
            # doing this doesn't actually throw an error
            test_proxies.subarray[sub_id].RemoveReceptors(
                invalid_receptors_to_remove
            )
            assert [
                test_proxies.subarray[sub_id].receptors[i]
                for i in range(len(receptors))
            ] == receptors
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize("", [])
    @pytest.mark.skip(
        reason="Since there's only one subarray, this test is not required (and  currently the SW does not support it)."
    )
    def test_AddRemoveReceptors_invalid_multiple(
        self: TestCbfSubarray,
    ) -> None:
        """
        Test CbfSubarrays's AddReceptors command for multiple subarrays
            when the receptor id is invalid
        """

    @pytest.mark.parametrize(
        "receptors, \
        sub_id",
        [(["SKA001", "SKA036", "SKA063"], 1), (["SKA063", "SKA100"], 1)],
    )
    def test_RemoveAllReceptors(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        receptors: List[str],
        sub_id: int,
    ) -> None:
        """
        Test CbfSubarrays's RemoveAllReceptors command

        :param proxies: proxies pytest fixture
        :param receptors: list of receptor ids
        :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all(
                [
                    test_proxies.vcc[i].subarrayMembership == 0
                    for i in range(1, test_proxies.num_vcc + 1)
                ]
            )

            # add some receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == sub_id
                    for r in receptors
                ]
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # remove all receptors
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all(
                [
                    test_proxies.vcc[
                        test_proxies.receptor_utils.receptor_id_to_vcc_id[r]
                    ].subarrayMembership
                    == 0
                    for r in receptors
                ]
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "ConfigureScan_basic_fspMultiReceptors.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "ConfigureScan_basic_fspNoReceptors.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
        ],
    )
    def test_ConfigureScan_basic(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's ConfigureScan command

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            # check initial value of attributes of CBF subarray
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].configurationID == ""
            assert test_proxies.subarray[sub_id].frequencyBand == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            # check configured attributes of CBF subarray
            assert sub_id == int(configuration["common"]["subarray_id"])
            assert (
                test_proxies.subarray[sub_id].configurationID
                == configuration["common"]["config_id"]
            )
            band_index = freq_band_dict()[
                configuration["common"]["frequency_band"]
            ]["band_index"]
            assert band_index == test_proxies.subarray[sub_id].frequencyBand
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.READY,
                wait_time_s,
                sleep_time_s,
            )

            # check the rest of the configured attributes of VCCs
            for r in vcc_receptors:
                assert test_proxies.vcc[r].frequencyBand == band_index
                assert test_proxies.vcc[r].subarrayMembership == sub_id
                assert (
                    test_proxies.vcc[r].configID
                    == configuration["common"]["config_id"]
                )
                if "band_5_tuning" in configuration["common"]:
                    for idx, band in enumerate(
                        configuration["common"]["band_5_tuning"]
                    ):
                        assert test_proxies.vcc[r].band5Tuning[idx] == band
                if "frequency_band_offset_stream1" in configuration["cbf"]:
                    assert (
                        test_proxies.vcc[r].frequencyBandOffsetStream1
                        == configuration["cbf"][
                            "frequency_band_offset_stream1"
                        ]
                    )
                if "frequency_band_offset_stream2" in configuration["cbf"]:
                    assert (
                        test_proxies.vcc[r].frequencyBandOffsetStream2
                        == configuration["cbf"][
                            "frequency_band_offset_stream2"
                        ]
                    )
                if "rfi_flagging_mask" in configuration["cbf"]:
                    assert test_proxies.vcc[r].rfiFlaggingMask == str(
                        configuration["cbf"]["rfi_flagging_mask"]
                    )

            time.sleep(1)
            # check configured attributes of VCC search windows
            if "search_window" in configuration["cbf"]:
                for idx, search_window in enumerate(
                    configuration["cbf"]["search_window"]
                ):
                    for r in vcc_receptors:
                        assert (
                            test_proxies.vccSw[r][idx + 1].tdcEnable
                            == search_window["tdc_enable"]
                        )
                        # TODO implement VCC SW functionality and
                        # correct power states
                        if search_window["tdc_enable"]:
                            assert (
                                test_proxies.vccSw[r][idx + 1].State()
                                == DevState.DISABLE
                            )
                        else:
                            assert (
                                test_proxies.vccSw[r][idx + 1].State()
                                == DevState.DISABLE
                            )
                        assert (
                            test_proxies.vccSw[r][idx + 1].searchWindowTuning
                            == search_window["search_window_tuning"]
                        )
                        if "tdc_num_bits" in search_window:
                            assert (
                                test_proxies.vccSw[r][idx + 1].tdcNumBits
                                == search_window["tdc_num_bits"]
                            )
                        if "tdc_period_before_epoch" in search_window:
                            assert (
                                test_proxies.vccSw[r][
                                    idx + 1
                                ].tdcPeriodBeforeEpoch
                                == search_window["tdc_period_before_epoch"]
                            )
                        if "tdc_period_after_epoch" in search_window:
                            assert (
                                test_proxies.vccSw[r][
                                    idx + 1
                                ].tdcPeriodAfterEpoch
                                == search_window["tdc_period_after_epoch"]
                            )
                        if "tdc_destination_address" in search_window:
                            for t in search_window["tdc_destination_address"]:
                                if (
                                    test_proxies.receptor_utils.receptor_id_to_int[
                                        t["receptor_id"]
                                    ]
                                    == r
                                ):
                                    tdcDestAddr = t["tdc_destination_address"]
                                    assert (
                                        list(
                                            test_proxies.vccSw[r][
                                                idx + 1
                                            ].tdcDestinationAddress
                                        )
                                        == tdcDestAddr
                                    )

            # check configured attributes of FSPs, including states of function mode capabilities
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("Check for fsp id = {}".format(fsp_id))

                if fsp["function_mode"] == "CORR":
                    function_mode = FspModes.CORR.value
                    assert (
                        test_proxies.fsp[fsp_id].functionMode == function_mode
                    )
                    assert (
                        sub_id in test_proxies.fsp[fsp_id].subarrayMembership
                    )
                    # check configured attributes of FSP subarray
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )

                    # If receptors are not specified, then
                    # all the subarray receptors are used
                    receptorsSpecified = False
                    if "receptors" in fsp:
                        if fsp["receptors"] != []:
                            receptorsSpecified = True

                    fsp_corr_receptors = test_proxies.fspSubarray["CORR"][
                        sub_id
                    ][fsp_id].receptors

                    if receptorsSpecified:
                        config_fsp_receptors_sorted = fsp["receptors"]
                        fsp_receptors_num = [
                            test_proxies.receptor_utils.receptor_id_to_int[r]
                            for r in config_fsp_receptors_sorted
                        ]
                        assert all(
                            [
                                fsp_corr_receptors[i] == fsp_receptors_num[i]
                                for i in range(len(fsp_corr_receptors))
                            ]
                        )

                    else:
                        receptors_sorted = receptors
                        receptors_sorted.sort()
                        fsp_receptors_num = [
                            test_proxies.receptor_utils.receptor_id_to_int[r]
                            for r in receptors_sorted
                        ]
                        assert all(
                            [
                                fsp_corr_receptors[i] == fsp_receptors_num[i]
                                for i in range(len(fsp_corr_receptors))
                            ]
                        )

                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].frequencyBand
                        == band_index
                    )
                    if "band_5_tuning" in configuration["common"]:
                        for idx, band in enumerate(
                            configuration["common"]["band_5_tuning"]
                        ):
                            assert (
                                test_proxies.fspSubarray["CORR"][sub_id][
                                    fsp_id
                                ].band5Tuning[idx]
                                == band
                            )
                    if "frequency_band_offset_stream1" in configuration["cbf"]:
                        assert (
                            test_proxies.fspSubarray["CORR"][sub_id][
                                fsp_id
                            ].frequencyBandOffsetStream1
                            == configuration["cbf"][
                                "frequency_band_offset_stream1"
                            ]
                        )
                    if "frequency_band_offset_stream2" in configuration["cbf"]:
                        assert (
                            test_proxies.fspSubarray["CORR"][sub_id][
                                fsp_id
                            ].frequencyBandOffsetStream2
                            == configuration["cbf"][
                                "frequency_band_offset_stream2"
                            ]
                        )
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].frequencySliceID
                        == fsp["frequency_slice_id"]
                    )
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].integrationFactor
                        == fsp["integration_factor"]
                    )
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].corrBandwidth
                        == fsp["zoom_factor"]
                    )
                    if fsp["zoom_factor"] > 0:
                        assert (
                            test_proxies.fspSubarray["CORR"][sub_id][
                                fsp_id
                            ].zoomWindowTuning
                            == fsp["zoom_window_tuning"]
                        )
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].fspChannelOffset
                        == fsp["channel_offset"]
                    )

                    for i in range(len(fsp["channel_averaging_map"])):
                        for j in range(len(fsp["channel_averaging_map"][i])):
                            assert (
                                test_proxies.fspSubarray["CORR"][sub_id][
                                    fsp_id
                                ].channelAveragingMap[i][j]
                                == fsp["channel_averaging_map"][i][j]
                            )

                    for i in range(len(fsp["output_link_map"])):
                        for j in range(len(fsp["output_link_map"][i])):
                            assert (
                                test_proxies.fspSubarray["CORR"][sub_id][
                                    fsp_id
                                ].outputLinkMap[i][j]
                                == fsp["output_link_map"][i][j]
                            )

                    if "output_host" and "output_mac" and "output_port" in fsp:
                        assert str(
                            test_proxies.fspSubarray["CORR"][sub_id][
                                fsp_id
                            ].visDestinationAddress
                        ).replace('"', "'") == str(
                            {
                                "outputHost": [
                                    fsp["output_host"][0],
                                    fsp["output_host"][1],
                                ],
                                "outputMac": [fsp["output_mac"][0]],
                                "outputPort": [
                                    fsp["output_port"][0],
                                    fsp["output_port"][1],
                                ],
                            }
                        ).replace(
                            '"', "'"
                        )

                elif fsp["function_mode"] == "PSS-BF":
                    function_mode = FspModes.PSS_BF.value
                    assert (
                        test_proxies.fsp[fsp_id].functionMode == function_mode
                    )
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].searchWindowID
                        == fsp["search_window_id"]
                    )

                    # TODO: currently searchBeams is stored by the device
                    #       as a json string ( via attribute 'searchBeams');
                    #       this has to be updated in FspPssSubarray
                    #       to read/write individual members
                    for idx, sBeam in enumerate(
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].searchBeams
                    ):
                        searchBeam = json.loads(sBeam)
                        assert (
                            searchBeam["search_beam_id"]
                            == fsp["search_beam"][idx]["search_beam_id"]
                        )
                        # TODO currently only one receptor supported
                        assert (
                            searchBeam["receptor_ids"][0][1]
                            == test_proxies.receptor_utils.receptor_id_to_int[
                                fsp["search_beam"][idx]["receptor_ids"][0]
                            ]
                        )
                        assert (
                            searchBeam["enable_output"]
                            == fsp["search_beam"][idx]["enable_output"]
                        )
                        assert (
                            searchBeam["averaging_interval"]
                            == fsp["search_beam"][idx]["averaging_interval"]
                        )
                        # TODO - this does not pass - to debug & fix
                        # assert searchBeam["searchBeamDestinationAddress"] == fsp["search_beam"][idx]["search_beam_destination_address"]

                elif fsp["function_mode"] == "PST-BF":
                    function_mode = FspModes.PST_BF.value
                    assert (
                        test_proxies.fsp[fsp_id].functionMode == function_mode
                    )

                    assert test_proxies.fsp[fsp_id].State() == DevState.ON
                    assert (
                        sub_id in test_proxies.fsp[fsp_id].subarrayMembership
                    )

                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                    for beam in fsp["timing_beam"]:
                        # TODO currently only one receptor supported
                        assert (
                            test_proxies.fspSubarray["PST-BF"][sub_id][
                                fsp_id
                            ].receptors[0]
                            == test_proxies.receptor_utils.receptor_id_to_int[
                                beam["receptor_ids"][0]
                            ]
                        )

                        assert all(
                            [
                                test_proxies.fspSubarray["PST-BF"][sub_id][
                                    fsp_id
                                ].timingBeamID[i]
                                == j
                                for i, j in zip(
                                    range(1), [beam["timing_beam_id"]]
                                )
                            ]
                        )

                elif fsp["function_mode"] == "VLBI":
                    function_mode = FspModes.VLBI.value
                    assert (
                        test_proxies.fsp[fsp_id].functionMode == function_mode
                    )
                    # TODO: This mode is not tested

            # Clean Up
            wait_time_s = 3
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    # TODO: The delay model and jones matrix are already tested.
    # Should this test just be for the beam weights?
    @pytest.mark.skip(
        reason="PST currently unsupported; timing beam verification needs refactor"
    )
    @pytest.mark.parametrize(
        "config_file_name, \
        jones_matrix_file_name, \
        delay_model_file_name, \
        timing_beam_weights_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic.json",
                "jonesmatrix.json",
                "delaymodel.json",
                "timingbeamweights.json",
                ["SKA063", "SKA001", "SKA036", "SKA100"],
            )
        ],
    )
    def test_ConfigureScan_onlyPst_basic_FSP_scan_parameters(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        delay_model_test: pytest.fixture,
        config_file_name: str,
        jones_matrix_file_name: str,
        delay_model_file_name: str,
        timing_beam_weights_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test CbfSubarrays's ConfigureScan command for Fsp PST

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param jones_matrix_file_name: JSON file for the jones matrix
        :param delay_model_file_name: JSON file for the delay model
        :param timing_beam_weights_file_name: JSON file for the timing beam weights
        :param receptors: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            # check initial value of attributes of CBF subarray
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].configurationID == ""
            assert test_proxies.subarray[sub_id].frequencyBand == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            # Insert the epoch
            jones_matrix_index_per_epoch = list(range(len(jones_matrix)))
            random.shuffle(jones_matrix_index_per_epoch)
            epoch_increment = 10
            for i, jones_matrix_index in enumerate(
                jones_matrix_index_per_epoch
            ):
                if i == 0:
                    epoch_time = 0
                    jones_matrix[jones_matrix_index]["epoch"] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    jones_matrix["jones_matrix"][jones_matrix_index][
                        "epoch"
                    ] = str(int(time.time()) + epoch_time)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            for epoch in range(len(jones_matrix_index_per_epoch)):
                for receptor in jones_matrix["jones_matrix"][
                    jones_matrix_index_per_epoch[epoch]
                ]["jones_matrix"]:
                    rec_id = receptor["receptor"]
                    for fsp in [
                        test_proxies.fsp[i]
                        for i in range(1, test_proxies.num_fsp + 1)
                    ]:
                        if fsp.functionMode in [
                            FspModes.PSS_BF.value,
                            FspModes.PST_BF.value,
                        ]:
                            for frequency_slice in receptor[
                                "jones_matrix_details"
                            ]:
                                fs_id = frequency_slice["fsid"]
                                matrix = frequency_slice["matrix"]
                                if fs_id == int(
                                    fsp.get_property("FspID")["FspID"][0]
                                ):
                                    if (
                                        fsp.functionMode
                                        == FspModes.PSS_BF.value
                                    ):
                                        fs_length = 16
                                        proxy_subarray = (
                                            test_proxies.fspSubarray["PSS-BF"][
                                                sub_id
                                            ][fs_id]
                                        )
                                    else:
                                        fs_length = 4
                                        proxy_subarray = (
                                            test_proxies.fspSubarray["PST-BF"][
                                                sub_id
                                            ][fs_id]
                                        )
                                    if (
                                        rec_id in proxy_subarray.receptors
                                        and len(matrix) == fs_length
                                    ):
                                        for idx, matrix_val in enumerate(
                                            matrix
                                        ):
                                            assert (
                                                matrix_val
                                                == fsp.jones_matrix[
                                                    rec_id - 1
                                                ][idx]
                                            )
                        else:
                            log_msg = "function mode {} currently not supported".format(
                                fsp.functionMode
                            )
                            logging.error(log_msg)

                time.sleep(epoch_increment)

            # Read the input delay model Json string from file:
            with open(data_file_path + delay_model_file_name) as f_in:
                delay_model_all = f_in.read().replace("\n", "")

            # Convert the serialized JSON object to a Python object:
            dm_obj_all = json.loads(delay_model_all)

            # Get the DM Python object input to the DM test
            delay_model_for_test_all_obj = (
                delay_model_test.create_test_dm_obj_all(dm_obj_all, receptors)
            )

            # to speed up the testing we use 4s between
            # delayModel updates (instead of the operational 10s)
            update_period = 4

            # to simulate updating the delay model multiple times, we
            # have several delay models in the input data
            dm_num_entries = len(delay_model_for_test_all_obj)

            # update the TM with each of the input delay models
            for i_dm in range(dm_num_entries):
                # Get one delay model Python object from the list
                input_delay_model_obj = delay_model_for_test_all_obj[i_dm]

                # Convert to a serialized JSON object
                input_delay_model = json.dumps(input_delay_model_obj)

                # Write this one delay_model JSON object to the TM emulator
                test_proxies.tm.delayModel = input_delay_model

                time.sleep(2)

                # convert receptor IDs to pair of str and int for FSPs
                for delay_detail in input_delay_model_obj["delay_details"]:
                    receptor_id = delay_detail["receptor"]
                    delay_detail["receptor"] = [
                        receptor_id,
                        test_proxies.receptor_utils.receptor_id_to_int[receptor_id],
                    ]
                input_delay_model = json.dumps(input_delay_model_obj)

                # check the delay model was correctly updated for fsp
                for fsp in [
                    test_proxies.fsp[i]
                    for i in range(1, test_proxies.num_fsp + 1)
                ]:
                    if fsp.functionMode in [
                        FspModes.PSS_BF.value,
                        FspModes.PST_BF.value,
                        FspModes.CORR.value,
                    ]:
                        # Fsp stores the whole delay model
                        # compare strings
                        assert (
                            input_delay_model.replace("\n", "")
                            == fsp.delayModel
                        )
                    else:
                        log_msg = (
                            "function mode {} currently not supported".format(
                                fsp.functionMode
                            )
                        )

                time.sleep(update_period)

            # update timing beam weights from tm emulator
            f = open(data_file_path + timing_beam_weights_file_name)
            timing_beam_weights = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for weights in timing_beam_weights["timing_beam_weights"]:
                for receptor in weights:
                    receptor["epoch"] = epoch
                    epoch = str(int(epoch) + 10)

            # update timing beam weights
            test_proxies.tm.timingBeamWeights = json.dumps(timing_beam_weights)
            time.sleep(1)

            for weights in timing_beam_weights:
                for receptor in weights["timing_beam_weights"]:
                    rec_id = test_proxies.receptor_utils.receptor_id_to_int[
                        receptor["receptor"]
                    ]
                    fs_id = receptor["timing_beam_weights_details"][0]["fsid"]
                    for index, value in enumerate(
                        receptor["timing_beam_weights_details"][0]["weights"]
                    ):
                        try:
                            assert (
                                test_proxies.fsp[fs_id].timingBeamWeights[
                                    rec_id - 1
                                ][index]
                                == value
                            )
                        except AssertionError as ae:
                            raise ae
                        except Exception as e:
                            raise e
                time.sleep(epoch_increment)

            # Clean Up
            wait_time_s = 3
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            )
        ],
    )
    def test_EndScan(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test CbfSubarrays's EndScan command

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param scan_file_name: JSON file for the scan configuration
        :param receptors: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            num_receptors = len(receptors)

            vcc_ids = [None for _ in range(num_receptors)]
            for receptor_id, ii in zip(receptors, range(num_receptors)):
                vcc_ids[ii] = test_proxies.receptor_utils.receptor_id_to_vcc_id[
                    receptor_id
                ]

            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(num_receptors), receptors)
                ]
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # Check fsp obsState BEFORE scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.IDLE
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.IDLE
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.IDLE
                    )

            wait_time_configure = 4
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            # check some configured attributes of CBF subarray
            frequency_band = configuration["common"]["frequency_band"]
            input_band_index = freq_band_dict()[frequency_band]["band_index"]

            assert (
                test_proxies.subarray[sub_id].configurationID
                == configuration["common"]["config_id"]
            )
            assert (
                test_proxies.subarray[sub_id].frequencyBand == input_band_index
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            # Check fsp obsState AFTER scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )

            # Send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string = f2.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string)
            f2.close()
            time.sleep(wait_time_configure)

            # Check obsStates BEFORE the EndScan() command
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.vcc[vcc_ids[0]].obsState == ObsState.SCANNING
            assert (
                test_proxies.vcc[vcc_ids[num_receptors - 1]].obsState
                == ObsState.SCANNING
            )

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )

            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_s,
                sleep_time_s,
            )

            # Check obsStates AFTER the EndScan() command
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            assert test_proxies.vcc[vcc_ids[0]].obsState == ObsState.READY
            assert (
                test_proxies.vcc[vcc_ids[num_receptors - 1]].obsState
                == ObsState.READY
            )
            # assert test_proxies.fspSubarray["CORR"][sub_id][fsp_corr_id-1].obsState == ObsState.READY
            # assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_pss_id-1].obsState == ObsState.READY
            # assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_pst_id-1].obsState == ObsState.READY

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        delay_model_file_name, \
        scan_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "delaymodel.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                ["SKA063", "SKA001"],
            )
        ],
    )
    def test_ConfigureScan_delayModel(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        delay_model_test: pytest.fixture,
        config_file_name: str,
        delay_model_file_name: str,
        scan_file_name: str,
        receptors: List[str],
        vcc_receptors: List[str],
    ) -> None:
        """
        Test CbfSubarrays's delay model update via the
            ConfigureScan command

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param delay_model_file_name: JSON file for the delay model
        :param scan_file_name: JSON file for the scan configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        # Test Description:
        # -----------------
        # . The TM device attribute delayModel is updated from time to time by
        #   invoking the write_delayModel attribute,
        #   operationally every 10 seconds; for this test we can use any interval
        # . In the background, the TM emulator polls the read_delayModel attribute
        #   at a high rate, the polling interval is typically << 1s)
        # . The CbfSubarray device subscribes to the read_delayModel attribute
        #   which means that every time an event occurs (i.e. a change in this
        #   attribute's value occurs) a callback is executed (the callback is
        #   also executed at the time of the subscription).
        # . The callback pushes the new value down to the VCC and FSP devices.
        #
        # The goal of this test is to verify that the delay model that
        # reached VCC (or FSP) is the same as the input delay model read by TM,
        # for all the delay Model in the list in the input JSON File.

        # Read the input delay model Json string from file:
        with open(data_file_path + delay_model_file_name) as f_in:
            delay_model_all = f_in.read().replace("\n", "")

        # Convert the serialized JSON object to a Python object:
        delay_model_all_obj = json.loads(delay_model_all)

        print(f"{delay_model_all}")

        # Get the DM Python object input to the DM test
        delay_model_for_test_all_obj = delay_model_test.create_test_dm_obj_all(
            delay_model_all_obj, vcc_receptors
        )

        # to speed up the testing we use 4s between
        # delayModel updates (instead of the operational 10s)
        update_period = 4

        # to simulate updating the delay model multiple times, we
        # have several delay models in the input data
        dm_num_entries = len(delay_model_all_obj)

        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            # update the TM with each of the input delay models
            for i_dm in range(dm_num_entries):
                # Get one delay model Python object from the list
                input_delay_model_obj = delay_model_for_test_all_obj[i_dm]

                # Convert to a serialized JSON object
                input_delay_model = json.dumps(input_delay_model_obj)

                # Write this one delay_model JSON object to the TM emulator
                logging.debug(
                    f"Writing delay model to TM emulator: {input_delay_model}"
                )
                test_proxies.tm.delayModel = input_delay_model

                time.sleep(10)

                # check the delay model was correctly updated for vcc
                vcc_receptors_num = []
                for receptor in vcc_receptors:
                    vcc_receptors_num.append(
                        test_proxies.receptor_utils.receptor_id_to_int[receptor]
                    )
                for jj, rec in enumerate(vcc_receptors):
                    # get the vcc device proxy (dp) corresponding to i_rec
                    this_vcc = test_proxies.receptor_utils.receptor_id_to_vcc_id[rec]
                    vcc_dp = test_proxies.vcc[this_vcc]

                    # Extract the  delay model corresponding to receptor i_rec:
                    # It is assumed that there is only one entry in the
                    # delay model for a given receptor
                    for entry in input_delay_model_obj["delay_details"]:
                        if entry["receptor"] == rec:
                            this_input_delay_model_obj = copy.deepcopy(entry)
                            # receptor as pair of str and int for comparison
                            this_input_delay_model_obj["receptor"] = [
                                entry["receptor"],
                                test_proxies.receptor_utils.receptor_id_to_int[
                                    entry["receptor"]
                                ],
                            ]
                            break

                    logging.debug(f"vcc delay model: {vcc_dp.delayModel}")
                    vcc_updated_delayModel_obj = json.loads(vcc_dp.delayModel)

                    # there should be only one delay model in the vcc
                    assert len(vcc_updated_delayModel_obj) == 1

                    # the one delay model should have only 1 entry
                    # for the given receptor
                    # remove the "delay_details" key and get the first item
                    # in the list so we can compare
                    # just the list of dictionaries that includes the
                    # receptor, epoch, etc
                    vcc_updated_delay_receptor = vcc_updated_delayModel_obj[
                        "delay_details"
                    ][0]

                    # want to compare strings
                    this_input_delay_model = json.dumps(
                        this_input_delay_model_obj
                    )
                    assert (
                        json.dumps(vcc_updated_delay_receptor)
                        == this_input_delay_model
                    )

                if i_dm == 0:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    test_proxies.subarray[sub_id].Scan(
                        f2.read().replace("\n", "")
                    )
                    f2.close()
                    test_proxies.wait_timeout_obs(
                        [test_proxies.subarray[sub_id]],
                        ObsState.SCANNING,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.subarray[sub_id].obsState
                        == ObsState.SCANNING
                    )

                # check the delay model was correctly updated for FSP
                # convert receptor IDs to pair of str and int for FSPs
                for model in input_delay_model_obj["delay_details"]:
                    receptor_id = model["receptor"]
                    model["receptor"] = [
                        receptor_id,
                        test_proxies.receptor_utils.receptor_id_to_int[receptor_id],
                    ]
                input_delay_model = json.dumps(input_delay_model_obj)
                for fsp in [
                    test_proxies.fsp[i]
                    for i in range(1, test_proxies.num_fsp + 1)
                ]:
                    if fsp.functionMode in [
                        FspModes.PSS_BF.value,
                        FspModes.PST_BF.value,
                        FspModes.CORR.value,
                    ]:
                        # fsp stores the whole delay model
                        # compare strings
                        assert fsp.delayModel == input_delay_model.replace(
                            "\n", ""
                        )
                time.sleep(update_period)

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.skip(reason="Jones matrix not used for AA0.5).")
    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        jones_matrix_file_name, \
        receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                "jonesmatrix.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            ),
        ],
    )
    def test_ConfigureScan_jones_matrix(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        scan_file_name: str,
        jones_matrix_file_name: str,
        receptors: List[str],
    ) -> None:
        """
        Test CbfSubarrays's jones matrix update via the
            ConfigureScan command

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param scan_file_name: JSON file for the scan configuration
        :param jones_matrix_file_name: JSON file for the jones matrix
        :param receptors: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            # Insert the epoch
            jones_matrix_index_per_epoch = list(
                range(len(jones_matrix["jones_matrix"]))
            )
            random.shuffle(jones_matrix_index_per_epoch)
            epoch_increment = 10
            for i, jones_matrix_index in enumerate(
                jones_matrix_index_per_epoch
            ):
                if i == 0:
                    epoch_time = 0
                    jones_matrix["jones_matrix"][jones_matrix_index][
                        "epoch"
                    ] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    jones_matrix["jones_matrix"][jones_matrix_index][
                        "epoch"
                    ] = str(int(time.time()) + epoch_time)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            epoch_to_scan = 1

            for epoch in range(len(jones_matrix_index_per_epoch)):
                for receptor in jones_matrix["jones_matrix"][
                    jones_matrix_index_per_epoch[epoch]
                ]["jones_matrix"]:
                    rec_id = test_proxies.receptor_utils.receptor_id_to_int[
                        receptor["receptor"]
                    ]
                    for frequency_slice in receptor["jones_matrix_details"]:
                        for index, value in enumerate(
                            frequency_slice["matrix"]
                        ):
                            vcc_id = test_proxies.receptor_utils.receptor_id_to_vcc_id[
                                receptor["receptor"]
                            ]
                            fs_id = frequency_slice["fsid"]
                            try:
                                assert (
                                    test_proxies.vcc[vcc_id].jones_matrix[
                                        fs_id - 1
                                    ][index]
                                    == value
                                )
                            except AssertionError as ae:
                                logging.error(
                                    "AssertionError; incorrect Jones matrix entry: \
                                    epoch {}, VCC {}, i = {}, jones_matrix[{}] = {}".format(
                                        jones_matrix["jones_matrix"][
                                            jones_matrix_index_per_epoch[epoch]
                                        ]["epoch"],
                                        vcc_id,
                                        index,
                                        fs_id - 1,
                                        test_proxies.vcc[vcc_id].jones_matrix[
                                            fs_id - 1
                                        ],
                                    )
                                )
                                raise ae
                            except Exception as e:
                                raise e
                    for fsp in [
                        test_proxies.fsp[i]
                        for i in range(1, test_proxies.num_fsp + 1)
                    ]:
                        if fsp.functionMode in [
                            FspModes.PSS_BF.value,
                            FspModes.PST_BF.value,
                        ]:
                            for frequency_slice in receptor[
                                "jones_matrix_details"
                            ]:
                                fs_id = frequency_slice["fsid"]
                                matrix = frequency_slice["matrix"]
                                if fs_id == int(
                                    fsp.get_property("FspID")["FspID"][0]
                                ):
                                    if (
                                        fsp.functionMode
                                        == FspModes.PSS_BF.value
                                    ):
                                        proxy_subarray = (
                                            test_proxies.fspSubarray["PSS-BF"][
                                                sub_id
                                            ][fs_id]
                                        )
                                        fs_length = 16
                                    elif (
                                        fsp.functionMode
                                        == FspModes.PST_BF.value
                                    ):
                                        proxy_subarray = (
                                            test_proxies.fspSubarray["PST-BF"][
                                                sub_id
                                            ][fs_id]
                                        )
                                        fs_length = 4
                                    if (
                                        rec_id in proxy_subarray.receptors
                                        and len(matrix) == fs_length
                                    ):
                                        for idx, matrix_val in enumerate(
                                            matrix
                                        ):
                                            assert (
                                                matrix_val
                                                == fsp.jones_matrix[
                                                    rec_id - 1
                                                ][idx]
                                            )
                        else:
                            log_msg = "function mode {} currently not supported".format(
                                fsp.functionMode
                            )
                            logging.error(log_msg)

                if epoch == epoch_to_scan:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    test_proxies.subarray[sub_id].Scan(
                        f2.read().replace("\n", "")
                    )
                    f2.close()
                    test_proxies.wait_timeout_obs(
                        [test_proxies.subarray[sub_id]],
                        ObsState.SCANNING,
                        wait_time_s,
                        sleep_time_s,
                    )
                    assert (
                        test_proxies.subarray[sub_id].obsState
                        == ObsState.SCANNING
                    )

                time.sleep(epoch_increment)

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            )
        ],
    )
    def test_Scan(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's Scan command

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param scan_file_name: JSON file for the scan configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )

            # check initial states
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.READY
                    )

            # send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string_scan = f2.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f2.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.SCANNING,
                wait_time_s,
                sleep_time_s,
            )

            scan_id = int(scan_configuration["scan_id"])

            # check scanID on VCC and FSP
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][fsp_id].scanID
                        == scan_id
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].scanID
                        == scan_id
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].scanID
                        == scan_id
                    )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].scanID == scan_id

            # check states
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.SCANNING
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert (
                        test_proxies.fspSubarray["CORR"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )
                elif fsp["function_mode"] == "PSS-BF":
                    assert (
                        test_proxies.fspSubarray["PSS-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )
                elif fsp["function_mode"] == "PST-BF":
                    assert (
                        test_proxies.fspSubarray["PST-BF"][sub_id][
                            fsp_id
                        ].obsState
                        == ObsState.SCANNING
                    )

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].End()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                ["SKA063", "SKA001", "SKA100"],
                [4, 1],
            ),
        ],
    )
    def test_Abort_Reset(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's Abort and ObsReset commands

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param scan_file_name: JSON file for the scan configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # -------------------- #
            # abort from READY #
            # -------------------- #
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.READY
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.READY

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.ABORTED,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.ABORTED
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.ABORTED

            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(3), receptors)
                ]
            )
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            # ------------------- #
            # abort from SCANNING #
            # ------------------- #
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(len(receptors)), receptors)
                ]
            )
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.SCANNING,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.subarray[sub_id].scanID == int(
                scan_configuration["scan_id"]
            )
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.SCANNING
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.SCANNING

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.ABORTED,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.ABORTED
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.ABORTED

            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert test_proxies.subarray[sub_id].scanID == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs(
                [
                    test_proxies.vcc[i]
                    for i in range(1, test_proxies.num_vcc + 1)
                ],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        scan_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                ["SKA063", "SKA001", "SKA100"],
                [4, 1],
            ),
        ],
    )
    def test_Abort_Restart(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        scan_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's Abort and Restart commands

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param scan_file_name: JSON file for the scan configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # --------------- #
            # abort from IDLE #
            # --------------- #
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.ABORTED,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.ABORTED
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.ABORTED

            # Restart: receptors should be empty
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            # ---------------- #
            # abort from READY #
            # ---------------- #
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.READY
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.READY

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.ABORTED,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.ABORTED
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.ABORTED

            # Restart
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            # ------------------- #
            # abort from SCANNING #
            # ------------------- #
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.READY,
                wait_time_configure,
                sleep_time_s,
            )
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.SCANNING,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.subarray[sub_id].scanID == int(
                scan_configuration["scan_id"]
            )
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.SCANNING
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.SCANNING

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.ABORTED,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.ABORTED
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.ABORTED

            # Restart
            wait_time_s = 3
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    # TODO: remove entirely?
    @pytest.mark.skip(
        reason="OffCommand will not be invoked in this manner by CSP LMC Mid, \
        rather a series of commands will be issued (Abort -> Restart/Reset)"
    )
    def test_Abort_from_Resourcing(self, test_proxies):
        """
        Test CbfSubarrays's Abort command from ObsState.RESOURCING.

        :param test_proxies: proxies pytest fixture
        """
        try:
            pass

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "Configure_TM-CSP_v2.json",
                ["SKA063", "SKA001", "SKA100"],
                [4, 1],
            ),
        ],
    )
    def test_Fault_Restart(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's Restart from ObsState.FAULT

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 3
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # send invalid configuration to trigger fault state
            # note that invalid config will trigger exception, ignore it
            with pytest.raises(Exception):
                test_proxies.subarray[sub_id].ConfigureScan("INVALID JSON")
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.FAULT,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.FAULT

            # Restart
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.EMPTY,
                wait_time_s,
                sleep_time_s,
            )
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e

    @pytest.mark.parametrize(
        "config_file_name, \
        receptors, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
                [4, 1],
            ),
            (
                "Configure_TM-CSP_v2.json",
                ["SKA063", "SKA001", "SKA100"],
                [4, 1],
            ),
        ],
    )
    def test_Fault_ObsReset(
        self: TestCbfSubarray,
        test_proxies: pytest.fixture,
        config_file_name: str,
        receptors: List[str],
        vcc_receptors: List[int],
    ) -> None:
        """
        Test CbfSubarrays's Obsreset from ObsState.FAULT

        :param proxies: proxies pytest fixture
        :param config_file_name: JSON file for the configuration
        :param receptors: list of receptor ids
        :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 3
            sleep_time_s = 1

            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            test_proxies.on()
            time.sleep(sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptors)
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # send invalid configuration to trigger fault state
            # note that invalid config will trigger exception, ignore it
            with pytest.raises(Exception):
                test_proxies.subarray[sub_id].ConfigureScan("INVALID JSON")
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.FAULT,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.FAULT

            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs(
                [test_proxies.subarray[sub_id]],
                ObsState.IDLE,
                wait_time_s,
                sleep_time_s,
            )
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert all(
                [
                    test_proxies.subarray[sub_id].receptors[i] == j
                    for i, j in zip(range(3), receptors)
                ]
            )
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                assert (
                    test_proxies.fspSubarray[fsp["function_mode"]][sub_id][
                        fsp_id
                    ].obsState
                    == ObsState.IDLE
                )
            for r in vcc_receptors:
                assert test_proxies.vcc[r].obsState == ObsState.IDLE

            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            test_proxies.clean_test_proxies()
            time.sleep(2)
            raise e
