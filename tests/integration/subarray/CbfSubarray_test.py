#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfSubarray."""
from __future__ import annotations  # allow forward references in type hints

from typing import List

# Standard imports
import sys
import os
import time
from datetime import datetime
import json
import logging
import random

# Data file path
data_file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

# Tango imports
import tango
from tango import DevState
import pytest
from enum import Enum

# SKA specific imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.commons.global_enum import freq_band_dict
from ska_tango_base.control_model import LoggingLevel, HealthState
from ska_tango_base.control_model import AdminMode, ObsState
from ska_tango_base.base.base_device import _DEBUGGER_PORT

class TestCbfSubarray:

    @pytest.mark.parametrize(
        "receptor_ids, \
        receptors_to_remove, \
        sub_id", 
        [
            (
                [1, 3, 4, 2],
                [2, 1, 4],
                1
            ),
            (
                [4, 1, 2],
                [2, 1],
                1
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_AddRemoveReceptors_valid(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
            Test CbfSubarrays's AddReceptors and RemoveReceptors commands

            :param proxies: proxies pytest fixture
            :param receptor_ids: list of receptor ids
            :param receptors_to_remove: list of ids of receptors to remove
            :param sub_id: the subarray id
        """

        if test_proxies.debug_device_is_on:
            port = test_proxies.subarray[sub_id].DebugDevice()

        try:
            wait_time_s = 1
            sleep_time_s = 1

            # controller will turn On/Off all of its subordinate devices,
            # including the subarrays, FSPs and VCCs
            test_proxies.on()

            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add all except last receptor
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids[:-1])
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert [test_proxies.subarray[sub_id].receptors[i] 
                for i in range(len(receptor_ids[:-1]))] == receptor_ids[:-1]
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == sub_id 
                for i in receptor_ids[:-1]])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # add the last receptor
            test_proxies.subarray[sub_id].AddReceptors([receptor_ids[-1]])
            time.sleep(1)
            assert [test_proxies.subarray[sub_id].receptors[i] 
                for i in range(len(receptor_ids))] == receptor_ids
            assert test_proxies.vcc[test_proxies.receptor_to_vcc[receptor_ids[-1]]].subarrayMembership == sub_id

            # remove all except last receptor
            test_proxies.subarray[sub_id].RemoveReceptors(receptors_to_remove)
            time.sleep(1)
            receptor_ids_after_remove = [r for r in receptor_ids if r not in receptors_to_remove]
            for idx, receptor in enumerate(receptor_ids_after_remove):
                assert test_proxies.subarray[sub_id].receptors[idx] == receptor
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[receptor]].subarrayMembership == sub_id
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 0 
                for i in receptors_to_remove])

            # remove remaining receptor
            test_proxies.subarray[sub_id].RemoveReceptors(receptor_ids_after_remove)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            for receptor in receptor_ids_after_remove:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[receptor]].subarrayMembership == 0
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
        "receptor_ids, \
        invalid_receptor_id, \
        sub_id", 
        [
            (
                [1, 3],
                [200],
                1
            ),
            (
                [4, 2],
                [0],
                1
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_AddReceptors_invalid_single(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        invalid_receptor_id: List[int],
        sub_id: int
    ) -> None:
        """
            Test CbfSubarrays's AddReceptors command for a single subarray 
                when the receptor id is invalid

            :param proxies: proxies pytest fixture
            :param receptor_ids: list of receptor ids
            :param invalid_receptor_id: invalid receptor id 
            :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors 
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try adding an invalid receptor ID
            result = test_proxies.subarray[sub_id].AddReceptors(invalid_receptor_id)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.FAULT, wait_time_s, sleep_time_s)
            assert result[0][0] == ResultCode.FAILED
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])

            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
        "receptor_ids, \
        invalid_receptors_to_remove, \
        sub_id", 
        [
            (
                [1, 3],
                [2],
                1
            ),
            (
                [4, 2],
                [1, 3],
                1
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveReceptors_invalid_single(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int],
        invalid_receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
            Test CbfSubarrays's RemoveReceptors command for a single subarray:  
                - when a receptor id is invalid (e.g. out of range)
                - when a receptor to be removed is not assigned to the subarray

            :param proxies: proxies pytest fixture
            :param receptor_ids: list of receptor ids
            :param invalid_receptors_to_remove: invalid receptor ids 
            :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors 
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try removing a receptor not assigned to subarray 1
            # doing this doesn't actually throw an error
            test_proxies.subarray[sub_id].RemoveReceptors(invalid_receptors_to_remove)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
    def test_AddRemoveReceptors_invalid_multiple(self: TestCbfSubarray) -> None:
        """
            Test CbfSubarrays's AddReceptors command for multiple subarrays 
                when the receptor id is invalid
        """
        pass
    
    @pytest.mark.parametrize(
        "receptor_ids, \
        sub_id", 
        [
            (
                [1, 3, 4],
                1
            ),
            (
                [4, 2],
                1
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveAllReceptors(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        sub_id: int
    ) -> None:
        """
            Test CbfSubarrays's RemoveAllReceptors command

            :param proxies: proxies pytest fixture
            :param receptor_ids: list of receptor ids
            :param sub_id: the subarray id
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == sub_id for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # remove all receptors
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 0 for i in receptor_ids])
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
        receptor_ids, \
        vcc_receptors", 
        [
            (
                "ConfigureScan_basic.json",
                [1, 3, 4, 2],
                [4, 1]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_ConfigureScan_basic(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        receptor_ids: List[int], 
        vcc_receptors: List[int],
    ) -> None:
        """
            Test CbfSubarrays's ConfigureScan command

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param receptor_ids: list of receptor ids
            :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])
            test_proxies.subarray[sub_id].loggingLevel = LoggingLevel.DEBUG

            # check initial value of attributes of CBF subarray
            vcc_index = test_proxies.receptor_to_vcc[4]
            
            logging.info("vcc_index  = {}".format( vcc_index ))

            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].configID == ''
            assert test_proxies.subarray[sub_id].frequencyBand == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            #TODO currently only support for 1 receptor per fsp
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)

            # check configured attributes of CBF subarray
            assert sub_id == int(configuration["common"]["subarray_id"])
            assert test_proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            band_index = freq_band_dict()[configuration["common"]["frequency_band"]]
            assert band_index == test_proxies.subarray[sub_id].frequencyBand 
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.READY, wait_time_s, sleep_time_s)

            # check the rest of the configured attributes of VCCs

            #TODO fix these tests; issue with VccBand devices either not reconfiguring in between
            #     configurations or causing a fault within the Vcc device
            # assert [proxy.State() for proxy in test_proxies.vccBand[test_proxies.receptor_to_vcc[4] - 1]] == [
            #     DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
            # assert [proxy.State() for proxy in test_proxies.vccBand[test_proxies.receptor_to_vcc[1] - 1]] == [
            #     DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

            # check the rest of the configured attributes of VCCs
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].frequencyBand == band_index
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].subarrayMembership == sub_id
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].configID == configuration["common"]["config_id"]
                if "band_5_tuning" in configuration["common"]:
                    for idx, band in enumerate(configuration["common"]["band_5_tuning"]):
                        assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].band5Tuning[idx] == band
                if "frequency_band_offset_stream_1" in configuration["cbf"]: 
                        assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].frequencyBandOffsetStream1 \
                            == configuration["cbf"]["frequency_band_offset_stream_1"]
                if "frequency_band_offset_stream_2" in configuration["cbf"]:
                        assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].frequencyBandOffsetStream2 \
                            == configuration["cbf"]["frequency_band_offset_stream_2"]
                if "rfi_flagging_mask" in configuration["cbf"]: 
                    assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].rfiFlaggingMask \
                        == str(configuration["cbf"]["rfi_flagging_mask"])
            
            # check configured attributes of search windows
            # first for search window 1...
            
            # TODO - SearchWidow device test is disabled since the same 
            # functionality is implemented by the VccSearchWindow device; 
            # to be decide which one to keep.

            # print("test_proxies.sw[1].State() = {}".format(test_proxies.sw[1].State()))
            # print("test_proxies.sw[2].State() = {}".format(test_proxies.sw[2].State()))

            # assert test_proxies.sw[1].State() == DevState.ON
            # assert test_proxies.sw[1].searchWindowTuning == 6000000000
            # assert test_proxies.sw[1].tdcEnable == True
            # assert test_proxies.sw[1].tdcNumBits == 8
            # assert test_proxies.sw[1].tdcPeriodBeforeEpoch == 5
            # assert test_proxies.sw[1].tdcPeriodAfterEpoch == 25
            # assert "".join(test_proxies.sw[1].tdcDestinationAddress.split()) in [
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            # ]
            # # then for search window 2...
            # assert test_proxies.sw[2].State() == DevState.DISABLE
            # assert test_proxies.sw[2].searchWindowTuning == 7000000000
            # assert test_proxies.sw[2].tdcEnable == False

            time.sleep(1)
            # check configured attributes of VCC search windows
            if "search_window" in configuration["cbf"]:
                for idx, search_window in enumerate(configuration["cbf"]["search_window"]):
                    for r in vcc_receptors:
                        assert test_proxies.vccTdc[
                            test_proxies.receptor_to_vcc[r]][idx + 1
                        ].tdcEnable == search_window["tdc_enable"]
                        if search_window["tdc_enable"]:
                            assert test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].State() == DevState.ON
                        else:
                            assert test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].State() == DevState.DISABLE
                        assert test_proxies.vccTdc[
                            test_proxies.receptor_to_vcc[r]][idx + 1
                        ].searchWindowTuning == search_window["search_window_tuning"]
                        if "tdc_num_bits" in search_window:
                            assert test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].tdcNumBits == search_window["tdc_num_bits"]
                        if "tdc_period_before_epoch" in search_window:
                            assert test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].tdcPeriodBeforeEpoch == search_window["tdc_period_before_epoch"]
                        if "tdc_period_after_epoch" in search_window:
                            assert test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].tdcPeriodAfterEpoch == search_window["tdc_period_after_epoch"]
                        if "tdc_destination_address" in search_window:
                            tdcDestAddr = [
                                t["tdc_destination_address"] 
                                for t in search_window["tdc_destination_address"] 
                                if t["receptor_id"] == r
                            ]
                            assert [list(test_proxies.vccTdc[
                                test_proxies.receptor_to_vcc[r]][idx + 1
                            ].tdcDestinationAddress)] == tdcDestAddr
 
           # check configured attributes of FSPs, including states of function mode capabilities
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("Check for fsp id = {}".format(fsp_id))

                if fsp["function_mode"] == "CORR": 
                    function_mode = FspModes.CORR.value
                    assert test_proxies.fsp[fsp_id].functionMode == function_mode
                    assert sub_id in test_proxies.fsp[fsp_id].subarrayMembership
                    assert [proxy.State() for proxy in test_proxies.fspFunctionMode[fsp_id].values()] == [
                        DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
                    ]
                    # check configured attributes of FSP subarray
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                    # currently only support for one receptor so only index 0 is checked
                    if "receptor_ids" in fsp:
                        assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].receptors == fsp["receptor_ids"][0]
                    else:
                        assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].receptors == receptor_ids[0]
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].frequencyBand == band_index
                    if "band_5_tuning" in configuration["common"]:
                        for idx, band in enumerate(configuration["common"]["band_5_tuning"]):
                            assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].band5Tuning[idx] == band
                    if "frequency_band_offset_stream_1" in configuration["cbf"]:
                        assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].frequencyBandOffsetStream1 == configuration["cbf"]["frequency_band_offset_stream_1"]
                    if "frequency_band_offset_stream_2" in configuration["cbf"]:
                        assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].frequencyBandOffsetStream2 == configuration["cbf"]["frequency_band_offset_stream_2"]                   
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].frequencySliceID == fsp["frequency_slice_id"]
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].integrationTime == fsp["integration_factor"]
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].corrBandwidth == fsp["zoom_factor"]
                    if fsp["zoom_factor"] > 0:
                        assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].zoomWindowTuning == fsp["zoom_window_tuning"]
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].fspChannelOffset == fsp["channel_offset"]

                    for i in range(len(fsp["channel_averaging_map"])):
                        for j in range(len(fsp["channel_averaging_map"][i])):
                            assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].channelAveragingMap[i][j] == fsp["channel_averaging_map"][i][j]

                    for i in range(len(fsp["output_link_map"])):
                        for j in range(len(fsp["output_link_map"][i])):
                            assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].outputLinkMap[i][j] == fsp["output_link_map"][i][j]
                    
                    if "output_host" and "output_mac" and "output_port" in fsp:
                        assert str(test_proxies.fspSubarray["CORR"][sub_id][fsp_id].visDestinationAddress).replace('"',"'") == \
                            str({
                                "outputHost": [
                                    fsp["output_host"][0], 
                                    fsp["output_host"][1]
                                ], 
                                "outputMac": [
                                    fsp["output_mac"][0]
                                ], 
                                "outputPort": [
                                    fsp["output_port"][0], 
                                    fsp["output_port"][1]
                                ]
                                }).replace('"',"'")


                elif fsp["function_mode"] == "PSS-BF": 
                    function_mode = FspModes.PSS_BF.value
                    assert test_proxies.fsp[fsp_id].functionMode == function_mode
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].searchWindowID == fsp["search_window_id"]

                    # TODO: currently searchBeams is stored by the device
                    #       as a json string ( via attribute 'searchBeams');  
                    #       this has to be updated in FspPssSubarray
                    #       to read/write individual members
                    for idx, sBeam in enumerate(test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].searchBeams):
                        searchBeam = json.loads(sBeam)
                        assert searchBeam["search_beam_id"] == fsp["search_beam"][idx]["search_beam_id"]
                        # currently only one receptor supported
                        assert searchBeam["receptor_ids"][0] == fsp["search_beam"][idx]["receptor_ids"][0]
                        assert searchBeam["enable_output"] == fsp["search_beam"][idx]["enable_output"]
                        assert searchBeam["averaging_interval"] == fsp["search_beam"][idx]["averaging_interval"]
                        # TODO - this does not pass - to debug & fix
                        # assert searchBeam["searchBeamDestinationAddress"] == fsp["search_beam"][idx]["search_beam_destination_address"]

                elif fsp["function_mode"] == "PST-BF": 
                    function_mode = FspModes.PST_BF.value
                    assert test_proxies.fsp[fsp_id].functionMode == function_mode

                    assert test_proxies.fsp[fsp_id].State() == DevState.ON
                    assert sub_id in test_proxies.fsp[fsp_id].subarrayMembership
                    assert [proxy.State() for proxy in test_proxies.fspFunctionMode[fsp_id].values()] == [
                        DevState.DISABLE, DevState.DISABLE, DevState.ON, DevState.DISABLE
                    ]
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY
                    for beam in fsp["timing_beam"]:
                        assert all([test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].receptors[i] == j for i, j in zip(range(1), beam["receptor_ids"])])
                        assert all([test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].timingBeamID[i] == j for i, j in zip(range(1), [beam["timing_beam_id"]])])

                elif fsp["function_mode"] == "VLBI": 
                    function_mode = FspModes.VLBI.value
                    assert test_proxies.fsp[fsp_id].functionMode == function_mode
                    #TODO: This mode is not tested

            # Clean Up
            wait_time_s = 3
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

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

    #TODO: The delay model and jones matrix are already tested. 
    # Should this test just be for the beam weights?
    @pytest.mark.parametrize(
        "config_file_name, \
        jones_matrix_file_name, \
        delay_model_file_name, \
        timing_beam_weights_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "jonesmatrix.json",
                "delaymodel.json",
                "timingbeamweights.json",
                [4, 1, 3, 2]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_ConfigureScan_onlyPst_basic_FSP_scan_parameters(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        jones_matrix_file_name: str,
        delay_model_file_name: str,
        timing_beam_weights_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
            Test CbfSubarrays's ConfigureScan command for Fsp PST

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param jones_matrix_file_name: JSON file for the jones matrix
            :param delay_model_file_name: JSON file for the delay model
            :param timing_beam_weights_file_name: JSON file for the timing beam weights
            :param receptor_ids: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            # check initial value of attributes of CBF subarray
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].configID == ''
            assert test_proxies.subarray[sub_id].frequencyBand == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)
            
            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            # Insert the epoch
            jones_matrix_index_per_epoch = list(range(len(jones_matrix["jonesMatrix"])))
            random.shuffle(jones_matrix_index_per_epoch)
            epoch_increment = 10
            for i, jones_matrix_index in enumerate(jones_matrix_index_per_epoch):
                if i == 0:
                    epoch_time = 0
                    jones_matrix["jonesMatrix"][jones_matrix_index]["epoch"] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    jones_matrix["jonesMatrix"][jones_matrix_index]["epoch"] = str(int(time.time()) + epoch_time)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range(len(jones_matrix_index_per_epoch)):

                for receptor in jones_matrix["jonesMatrix"][jones_matrix_index_per_epoch[epoch]]["matrixDetails"]:
                    rec_id = receptor["receptor"]
                    for fsp in [test_proxies.fsp[i] for i in range(1, test_proxies.num_fsp + 1)]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for frequency_slice in receptor["receptorMatrix"]:
                                fs_id = frequency_slice["fsid"]
                                matrix = frequency_slice["matrix"]
                                if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                    if fsp.functionMode == FspModes.PSS_BF.value:
                                        fs_length = 16
                                        proxy_subarray = test_proxies.fspSubarray["PSS-BF"][sub_id][fs_id]
                                    else:
                                        fs_length = 4
                                        proxy_subarray = test_proxies.fspSubarray["PST-BF"][sub_id][fs_id]
                                    if rec_id in proxy_subarray.receptors and len(matrix) == fs_length:
                                        for idx, matrix_val in enumerate(matrix):
                                            assert matrix_val == fsp.jonesMatrix[rec_id -1][idx]
                        else:
                            log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                            logging.error(log_msg)

                time.sleep(epoch_increment)

            # update delay models from tm emulator
            f = open(data_file_path + delay_model_file_name)
            delay_model = json.loads(f.read().replace("\n", ""))
           
           # Insert the epoch
            delay_model_index_per_epoch = list(range(len(delay_model["delayModel"])))
            random.shuffle(delay_model_index_per_epoch)
            epoch_increment = 10
            for i, delay_model_index in enumerate(delay_model_index_per_epoch):
                if i == 0:
                    epoch_time = 0
                    delay_model["delayModel"][delay_model_index]["epoch"] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    delay_model["delayModel"][delay_model_index]["epoch"] = str(int(time.time()) + epoch_time)

            # update delay model
            test_proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range(len(delay_model_index_per_epoch)):

                model = delay_model["delayModel"][delay_model_index_per_epoch[epoch]]            
                for delayDetail in model["delayDetails"]:
                    rec_id = delayDetail["receptor"]
                    for fsp in [test_proxies.fsp[i] for i in range(1, test_proxies.num_fsp + 1)]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                fsp_id = receptorDelayDetail["fsid"]
                                delayCoeff = receptorDelayDetail["delayCoeff"]
                                if fsp_id == int(fsp.get_property("FspID")['FspID'][0]):
                                    if fsp.functionMode == FspModes.PSS_BF.value:
                                        proxy_subarray = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
                                    else:
                                        proxy_subarray = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
                                    if rec_id in proxy_subarray.receptors:
                                        for idx, coeff in enumerate(delayCoeff):
                                            assert coeff == fsp.delayModel[rec_id -1][idx]
                        else:
                            log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                            logging.error(log_msg)

                time.sleep(epoch_increment)

            # update timing beam weights from tm emulator
            f = open(data_file_path + timing_beam_weights_file_name)
            timing_beam_weights = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for weights in timing_beam_weights["beamWeights"]:
                weights["epoch"] = epoch
                epoch = str(int(epoch) + 10)
            
            # update delay model
            test_proxies.tm.beamWeights = json.dumps(timing_beam_weights)
            time.sleep(1)

            for weights in timing_beam_weights["beamWeights"]:
                for receptor in weights["beamWeightsDetails"]:
                    rec_id = int(receptor["receptor"])
                    fs_id = receptor["receptorWeightsDetails"][0]["fsid"]
                    for index, value in enumerate(receptor["receptorWeightsDetails"][0]["weights"]):
                        try:
                            assert test_proxies.fsp[fs_id].timingBeamWeights[rec_id - 1][index] == value
                        except AssertionError as ae:
                            raise ae
                        except Exception as e:
                            raise e
                time.sleep(epoch_increment)

            # Clean Up
            wait_time_s = 3
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_EndScan(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
            Test CbfSubarrays's EndScan command 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param scan_file_name: JSON file for the scan configuration
            :param receptor_ids: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            num_receptors = len(receptor_ids)

            vcc_ids = [None for _ in range(num_receptors)]
            for receptor_id, ii in zip(receptor_ids, range(num_receptors)):
                vcc_ids[ii] = test_proxies.receptor_to_vcc[receptor_id]

            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(num_receptors), receptor_ids)])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # Check fsp obsState BEFORE scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE

            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)

            # check some configured attributes of CBF subarray           
            frequency_band   = configuration["common"]["frequency_band"]
            input_band_index = freq_band_dict()[frequency_band]

            assert test_proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            assert test_proxies.subarray[sub_id].frequencyBand == input_band_index
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            # Check fsp obsState AFTER scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY

            # Send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string = f2.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string)
            f2.close()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)

            # Check obsStates BEFORE the EndScan() command
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.vcc[vcc_ids[0]].obsState == ObsState.SCANNING
            assert test_proxies.vcc[vcc_ids[num_receptors-1]].obsState == ObsState.SCANNING

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING

            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_s, sleep_time_s)

            # Check obsStates AFTER the EndScan() command
            assert test_proxies.subarray[sub_id].obsState  == ObsState.READY
            assert test_proxies.vcc[vcc_ids[0]].obsState  == ObsState.READY
            assert test_proxies.vcc[vcc_ids[num_receptors -1]].obsState == ObsState.READY
            # assert test_proxies.fspSubarray["CORR"][sub_id][fsp_corr_id-1].obsState == ObsState.READY
            # assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_pss_id-1].obsState == ObsState.READY
            # assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_pst_id-1].obsState == ObsState.READY

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

            test_proxies.on()

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
        receptor_ids, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "delaymodel.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
                [4, 1]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_ConfigureScan_delayModel(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        delay_model_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int],
    ) -> None:
        """
            Test CbfSubarrays's delay model update via the 
                ConfigureScan command 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param delay_model_file_name: JSON file for the delay model
            :param scan_file_name: JSON file for the scan configuration
            :param receptor_ids: list of receptor ids
            :param vcc_receptors: list of vcc receptor ids
        """
        
        # Read delay model data from file
        f = open(data_file_path + delay_model_file_name)
        json_string_delay_mod = f.read().replace("\n", "")
        delay_model = json.loads(json_string_delay_mod)
        f.close()

        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            
            # Insert the epoch
            delay_model_index_per_epoch = list(range(len(delay_model["delayModel"])))
            random.shuffle(delay_model_index_per_epoch)
            epoch_increment = 10
            for i, delay_model_index in enumerate(delay_model_index_per_epoch):
                if i == 0:
                    epoch_time = 0
                    delay_model["delayModel"][delay_model_index]["epoch"] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    delay_model["delayModel"][delay_model_index]["epoch"] = str(int(time.time()) + epoch_time)

            # update delay model
            test_proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            epoch_to_scan = 1
            num_cols = 6
            num_rows_vcc = 26

            for epoch in range(len(delay_model_index_per_epoch)):

                model = delay_model["delayModel"][delay_model_index_per_epoch[epoch]]            
                for delayDetail in model["delayDetails"]:
                    rec_id = delayDetail["receptor"]
                    for r in vcc_receptors:
                        vcc = test_proxies.vcc[test_proxies.receptor_to_vcc[r]]  
                        if delayDetail["receptor"] == r:
                            mod_vcc = [[0.0] * num_cols for i in range(num_rows_vcc)]
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                fs_id = receptorDelayDetail["fsid"]
                                delayCoeff = receptorDelayDetail["delayCoeff"]
                                mod_vcc[fs_id -1] = delayCoeff
                            for i in range(len(mod_vcc)):
                                for j in range(len(mod_vcc[i])):
                                    assert vcc.delayModel[i][j] == mod_vcc[i][j]
                    for fsp in [test_proxies.fsp[i] for i in range(1, test_proxies.num_fsp + 1)]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                fsp_id = receptorDelayDetail["fsid"]
                                delayCoeff = receptorDelayDetail["delayCoeff"]
                                if fsp_id == int(fsp.get_property("FspID")['FspID'][0]):
                                    if fsp.functionMode == FspModes.PSS_BF.value:
                                        proxy_subarray = test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id]
                                    else:
                                        proxy_subarray = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
                                    if rec_id in proxy_subarray.receptors:
                                        for idx, coeff in enumerate(delayCoeff):
                                            assert coeff == fsp.delayModel[rec_id -1][idx]
                        else:
                            log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                            logging.error(log_msg)
                              
                if epoch == epoch_to_scan:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    test_proxies.subarray[sub_id].Scan(f2.read().replace("\n", ""))
                    f2.close()
                    test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)
                    assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

                time.sleep(epoch_increment)

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
        jones_matrix_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                "jonesmatrix.json",
                [1, 3, 4, 2],
            ),
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_ConfigureScan_jonesMatrix(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        jones_matrix_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
            Test CbfSubarrays's jones matrix update via the 
                ConfigureScan command 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param scan_file_name: JSON file for the scan configuration
            :param jones_matrix_file_name: JSON file for the jones matrix
            :param receptor_ids: list of receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                       for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            # Insert the epoch
            jones_matrix_index_per_epoch = list(range(len(jones_matrix["jonesMatrix"])))
            random.shuffle(jones_matrix_index_per_epoch)
            epoch_increment = 10
            for i, jones_matrix_index in enumerate(jones_matrix_index_per_epoch):
                if i == 0:
                    epoch_time = 0
                    jones_matrix["jonesMatrix"][jones_matrix_index]["epoch"] = str(epoch_time)
                else:
                    epoch_time += epoch_increment
                    jones_matrix["jonesMatrix"][jones_matrix_index]["epoch"] = str(int(time.time()) + epoch_time)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            epoch_to_scan = 1
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range(len(jones_matrix_index_per_epoch)):

                for receptor in jones_matrix["jonesMatrix"][jones_matrix_index_per_epoch[epoch]]["matrixDetails"]:
                    rec_id = receptor["receptor"]
                    for frequency_slice in receptor["receptorMatrix"]:
                        for index, value in enumerate(frequency_slice["matrix"]):
                            vcc_id = test_proxies.receptor_to_vcc[rec_id]
                            fs_id = frequency_slice["fsid"]
                            try:
                                assert test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                            except AssertionError as ae:
                                logging.error(
                                    "AssertionError; incorrect Jones matrix entry: \
                                    epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format
                                        (
                                            jones_matrix["jonesMatrix"][jones_matrix_index_per_epoch[epoch]]["epoch"], 
                                            vcc_id, index, 
                                            fs_id-1, 
                                            test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1]
                                        )
                                )
                                raise ae
                            except Exception as e:
                                raise e
                    for fsp in [test_proxies.fsp[i] for i in range(1, test_proxies.num_fsp + 1)]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for frequency_slice in receptor["receptorMatrix"]:
                                fs_id = frequency_slice["fsid"]
                                matrix = frequency_slice["matrix"]
                                if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                    if fsp.functionMode == FspModes.PSS_BF.value:
                                        proxy_subarray = test_proxies.fspSubarray["PSS-BF"][sub_id][fs_id]
                                        fs_length = 16
                                    elif fsp.functionMode == FspModes.PST_BF.value:
                                        proxy_subarray = test_proxies.fspSubarray["PST-BF"][sub_id][fs_id]
                                        fs_length = 4
                                    if rec_id in proxy_subarray.receptors and len(matrix) == fs_length:
                                            for idx, matrix_val in enumerate(matrix):
                                                assert matrix_val == fsp.jonesMatrix[rec_id -1][idx]
                        else:
                            log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                            logging.error(log_msg)

                if epoch == epoch_to_scan:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    test_proxies.subarray[sub_id].Scan(f2.read().replace("\n", ""))
                    f2.close()
                    test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)
                    assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

                time.sleep(epoch_increment)

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
        receptor_ids, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
                [4, 1]
            )
        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Scan(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
            Test CbfSubarrays's Scan command 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param scan_file_name: JSON file for the scan configuration
            :param receptor_ids: list of receptor ids
            :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)

            # check initial states
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY

            # send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string_scan = f2.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f2.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)
            
            scan_id = scan_configuration["scan_id"]

            # check scanID on VCC and FSP
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].scanID == scan_id
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].scanID == scan_id
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].scanID == scan_id
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].scanID == scan_id

            # check states
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, wait_time_s, sleep_time_s)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

            test_proxies.on()

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
        receptor_ids, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
                [4, 1]
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
                [4, 1]
            )

        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Abort_Reset(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
            Test CbfSubarrays's Abort and ObsReset commands 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param scan_file_name: JSON file for the scan configuration
            :param receptor_ids: list of receptor ids
            :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            ############################# abort from READY ###########################
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.READY
            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(3), receptor_ids)])
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

            ############################# abort from SCANNING ###########################
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.subarray[sub_id].scanID == scan_configuration["scan_id"]
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert test_proxies.subarray[sub_id].scanID == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

            # Clean up
            wait_time_s = 3
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, wait_time_s, sleep_time_s)

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
        receptor_ids, \
        vcc_receptors",
        [
            (
                "ConfigureScan_basic.json",
                "Scan1_basic.json",
                [1, 3, 4, 2],
                [4, 1]
            ),
            (
                "Configure_TM-CSP_v2.json",
                "Scan2_basic.json",
                [4, 1, 2],
                [4, 1]
            )

        ]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Abort_Restart(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
            Test CbfSubarrays's Abort and Restart commands 

            :param proxies: proxies pytest fixture
            :param config_file_name: JSON file for the configuration
            :param scan_file_name: JSON file for the scan configuration
            :param receptor_ids: list of receptor ids
            :param vcc_receptors: list of vcc receptor ids
        """
        try:
            wait_time_s = 1
            sleep_time_s = 1

            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            ############################# abort from IDLE ###########################
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # Restart: receptors should be empty
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE


            ############################# abort from READY ###########################
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, wait_time_s, sleep_time_s)
            # configure scan
            wait_time_configure = 5
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, wait_time_configure, sleep_time_s)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert test_proxies.subarray[sub_id].scanID == scan_configuration["scan_id"]
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING

            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, wait_time_s, sleep_time_s)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # ObsReset
            wait_time_s = 3
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, wait_time_s, sleep_time_s)
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    assert test_proxies.fspSubarray["CORR"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    assert test_proxies.fspSubarray["PSS-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    assert test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id].obsState == ObsState.IDLE
            for r in vcc_receptors  :
                assert test_proxies.vcc[test_proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

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
    
    #TODO: remove entirely?
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
