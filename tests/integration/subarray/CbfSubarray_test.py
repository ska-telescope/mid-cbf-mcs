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
from ska_tango_base.base_device import _DEBUGGER_PORT

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
    def test_AddRemoveReceptors_valid(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
        Test valid AddReceptors and RemoveReceptors commands
        """

        if test_proxies.debug_device_is_on:
            port = test_proxies.subarray[sub_id].DebugDevice()

        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
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
        invalid_receptors_to_remove, \
        sub_id", 
        [
            (
                [1, 3],
                [200],
                [2],
                1
            ),
            (
                [4, 2],
                [0],
                [1, 3],
                1
            )
        ]
    )
    def test_AddReceptors_invalid_single(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        invalid_receptor_id: List[int],
        invalid_receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
        Test invalid AddReceptors commands involving a single subarray:
            - when a receptor ID is invalid (e.g. out of range)
        """
        try:
            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors 
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try adding an invalid receptor ID
            result = test_proxies.subarray[sub_id].AddReceptors(invalid_receptor_id)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.FAULT, 1, 1)
            assert result[0][0] == ResultCode.FAILED
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])

            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)

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
    def test_RemoveReceptors_invalid_single(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int],
        invalid_receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
        Test invalid AddReceptors commands involving a single subarray:
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """
        try:
            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors 
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try removing a receptor not assigned to subarray 1
            # doing this doesn't actually throw an error
            test_proxies.subarray[sub_id].RemoveReceptors(invalid_receptors_to_remove)
            assert [test_proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)

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
    def test_RemoveAllReceptors(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        receptor_ids: List[int], 
        sub_id: int
    ) -> None:
        """
        Test RemoveAllReceptors command
        """
        try:
            test_proxies.on()
            
            assert test_proxies.subarray[sub_id].State() == DevState.ON
            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(test_proxies.subarray[sub_id].receptors) == 0
            assert all([test_proxies.vcc[i].subarrayMembership == 0 
                for i in range(1, test_proxies.num_vcc + 1)])

            # add some receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            assert all([test_proxies.vcc[test_proxies.receptor_to_vcc[i]].subarrayMembership == sub_id for i in receptor_ids])
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE

            # remove all receptors
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
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
    def test_ConfigureScan_basic(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        receptor_ids: List[int], 
        vcc_receptors: List[int]
    ) -> None:
        """
        Test a successful scan configuration
        """
        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            # check configured attributes of CBF subarray
            assert sub_id == int(configuration["common"]["subarray_id"])
            assert test_proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            band_index = freq_band_dict()[configuration["common"]["frequency_band"]]
            assert band_index == test_proxies.subarray[sub_id].frequencyBand 
            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.READY, 1, 1)

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
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
        jones_matrix_file_name, \
        delay_model_file_name, \
        timing_beam_weights_file_name, \
        receptor_ids", 
        [
            (
                "ConfigureScan_basic.json",
                "jonesmatrix_fsp.json",
                "delaymodel_fsp.json",
                "timingbeamweights.json",
                [4, 1, 3, 2]
            )
        ]
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
        Test a successful transmission of PST-BF parameters to FSP
        """
        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            
            # update jones matrices from tm emulator
            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for matrix in jones_matrix["jonesMatrix"]:
                matrix["epoch"] = epoch
                if matrix["destinationType"] == "fsp":
                    epoch = str(int(epoch) + 10)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(1)

            for matrix in jones_matrix["jonesMatrix"]:
                if matrix["destinationType"] == "fsp":
                    for receptor in matrix["matrixDetails"]:
                        rec_id = int(receptor["receptor"])
                        fs_id = receptor["receptorMatrix"][0]["fsid"]
                        for index, value in enumerate(receptor["receptorMatrix"][0]["matrix"]):
                            try:
                                assert test_proxies.fsp[fs_id].jonesMatrix[rec_id - 1][index] == value
                            except AssertionError as ae:
                                raise ae
                            except Exception as e:
                                raise e
                    time.sleep(10)
            

            # update delay models from tm emulator
            f = open(data_file_path + delay_model_file_name)
            delay_model = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for model in delay_model["delayModel"]:
                model["epoch"] = epoch
                if model["destinationType"] == "fsp":
                    epoch = str(int(epoch) + 10)
            
            # update delay model
            test_proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            for model in delay_model["delayModel"]:
                if model["destinationType"] == "fsp":
                    for receptor in model["delayDetails"]:
                        rec_id = int(receptor["receptor"])
                        fs_id = receptor["receptorDelayDetails"][0]["fsid"]
                        for index, value in enumerate(receptor["receptorDelayDetails"][0]["delayCoeff"]):
                            try:
                                assert test_proxies.fsp[fs_id].delayModel[rec_id - 1][index] == value
                            except AssertionError as ae:
                                raise ae
                            except Exception as e:
                                raise e
                    time.sleep(10)

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
                time.sleep(10)

            # Clean Up
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    def test_EndScan(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the EndScan command
        """

        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
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

            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)

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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)

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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 1, 1)

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
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    
    #TODO: Delay model values do not match json file
    @pytest.mark.skip(
        reason="Delay model values do not match json file"
    )
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
    def test_ConfigureScan_delayModel(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        delay_model_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:

        """
        Test the reception of delay models
        """
        
        # Read delay model data from file
        f = open(data_file_path + delay_model_file_name)
        json_string_delay_mod = f.read().replace("\n", "")
        delay_model = json.loads(json_string_delay_mod)
        configuration_delay_mod = json.loads(json_string_delay_mod)
        f.close()

        aa = delay_model["delayModel"][0]["delayDetails"][0]["receptorDelayDetails"]
        num_fsp_IDs = len(aa)
        for jj in range(num_fsp_IDs):      
            logging.info( "delayCoeff = {}".format( aa[jj]["delayCoeff"]) )

        try:
            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            # create a delay model
            
            # Insert the epoch
            delay_model["delayModel"][0]["epoch"] = str(int(time.time()) + 20)
            delay_model["delayModel"][1]["epoch"] = "0"
            delay_model["delayModel"][2]["epoch"] = str(int(time.time()) + 10)

            # update delay model
            test_proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(1)

            for jj in range(len(receptor_ids)):
                logging.info((" test_proxies.vcc[{}].receptorID = {}".
                format(jj+1, test_proxies.vcc[jj+1].receptorID)))

            logging.info( ("Vcc, receptor 1, ObsState = {}".
            format(test_proxies.vcc[test_proxies.receptor_to_vcc[1]].ObsState)) )

            #test_proxies.vcc[0].receptorID
            delayModNum = 1
            for r in vcc_receptors:
                vcc = test_proxies.vcc[test_proxies.receptor_to_vcc[r]]
                delayMod = vcc.delayModel
                delayModConf = []
                delayDetails = configuration_delay_mod["delayModel"][delayModNum]["delayDetails"]
                for delayDetail in delayDetails:
                    if delayDetail["receptor"] == r:
                        for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                            delayModConf += receptorDelayDetail["delayCoeff"]
                confIdx = 0
                for i in range(len(delayMod)):
                    for j in range(len(delayMod[i])):
                        assert delayMod[i][j] == delayModConf[confIdx]
                        confIdx += 1

            # transition to obsState=SCANNING
            f2 = open(data_file_path + scan_file_name)
            test_proxies.subarray[sub_id].Scan(f2.read().replace("\n", ""))
            f2.close()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING

            time.sleep(10)

            delayModNum = 2
            for r in vcc_receptors:
                vcc = test_proxies.vcc[test_proxies.receptor_to_vcc[r]]
                delayMod = vcc.delayModel
                delayModConf = []
                delayDetails = configuration_delay_mod["delayModel"][delayModNum]["delayDetails"]
                for delayDetail in delayDetails:
                    if delayDetail["receptor"] == r:
                        for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                            delayModConf += receptorDelayDetail["delayCoeff"]
                confIdx = 0
                for i in range(len(delayMod)):
                    for j in range(len(delayMod[i])):
                        assert delayMod[i][j] == delayModConf[confIdx]
                        confIdx += 1

            time.sleep(10)
            delayModNum = 0
            for r in vcc_receptors:
                vcc = test_proxies.vcc[test_proxies.receptor_to_vcc[r]]
                delayMod = vcc.delayModel
                delayModConf = []
                delayDetails = configuration_delay_mod["delayModel"][delayModNum]["delayDetails"]
                for delayDetail in delayDetails:
                    if delayDetail["receptor"] == r:
                        for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                            delayModConf += receptorDelayDetail["delayCoeff"]
                confIdx = 0
                for i in range(len(delayMod)):
                    for j in range(len(delayMod[i])):
                        assert delayMod[i][j] == delayModConf[confIdx]
                        confIdx += 1

            # Clean up
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    def test_ConfigureScan_jonesMatrix(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        jones_matrix_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the reception of Jones matrices
        """
        try:
            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                       for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)

            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            assert test_proxies.subarray[sub_id].obsState == ObsState.READY

            #create a Jones matrix
            f = open(data_file_path + jones_matrix_file_name)
            jones_matrix = json.loads(f.read().replace("\n", ""))
            f.close()

            jones_matrix["jonesMatrix"][0]["epoch"] = str(int(time.time()) + 20)
            jones_matrix["jonesMatrix"][1]["epoch"] = "0"
            jones_matrix["jonesMatrix"][2]["epoch"] = str(int(time.time()) + 10)

            # update Jones Matrix
            test_proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(5)

            for receptor in jones_matrix["jonesMatrix"][1]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = test_proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error(
                                "AssertionError; incorrect Jones matrix entry: \
                                epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format
                                    (
                                        jones_matrix["jonesMatrix"][1]["epoch"], 
                                        vcc_id, index, 
                                        fs_id-1, 
                                        test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1]
                                    )
                            )
                            raise ae
                        except Exception as e:
                            raise e

            # transition to obsState == SCANNING
            f = open(data_file_path + scan_file_name)
            test_proxies.subarray[sub_id].Scan(f.read().replace("\n", ""))
            f.close()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.SCANNING
            
            time.sleep(10)
            for receptor in jones_matrix["jonesMatrix"][2]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = test_proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error(
                                "AssertionError; incorrect Jones matrix entry: \
                                epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format
                                (
                                    jones_matrix["jonesMatrix"][1]["epoch"], 
                                    vcc_id, 
                                    index, 
                                    fs_id-1, 
                                    test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1]
                                )
                            )
                            raise ae
                        except Exception as e:
                            raise e
            
            time.sleep(10)
            for receptor in jones_matrix["jonesMatrix"][0]["matrixDetails"]:
                for frequency_slice in receptor["receptorMatrix"]:
                    for index, value in enumerate(frequency_slice["matrix"]):
                        vcc_id = test_proxies.receptor_to_vcc[receptor["receptor"]]
                        fs_id = frequency_slice["fsid"]
                        try:
                            assert test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                        except AssertionError as ae:
                            logging.error(
                                "AssertionError; incorrect Jones matrix entry: \
                                epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format
                                (
                                    jones_matrix["jonesMatrix"][1]["epoch"], 
                                    vcc_id, 
                                    index, 
                                    fs_id-1, 
                                    test_proxies.vcc[vcc_id].jonesMatrix[fs_id-1]
                                )
                            )
                            raise ae
                        except Exception as e:
                            raise e

            # Clean up
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    def test_Scan(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test the Scan command
        """
        try:
            test_proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert test_proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            test_proxies.subarray[sub_id].AddReceptors(receptor_ids)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)

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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            
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
            test_proxies.subarray[sub_id].EndScan()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            test_proxies.subarray[sub_id].GoToIdle()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.IDLE, 3, 1)
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    def test_Abort_Reset(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test abort reset
        """
        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            test_proxies.subarray[sub_id].ObsReset()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([test_proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
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
            test_proxies.subarray[sub_id].RemoveAllReceptors()
            test_proxies.wait_timeout_obs([test_proxies.vcc[i] 
                for i in range(1, test_proxies.num_vcc + 1)], ObsState.EMPTY, 3, 1)

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
    def test_Abort_Restart(
        self: TestCbfSubarray, 
        test_proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test abort restart
        """
        try:
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.IDLE
            # abort
            test_proxies.subarray[sub_id].Abort()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # Restart: receptors should be empty
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert test_proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            # configure scan
            test_proxies.subarray[sub_id].ConfigureScan(json_string)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            test_proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
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
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
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
            test_proxies.subarray[sub_id].Restart()
            test_proxies.wait_timeout_obs([test_proxies.subarray[sub_id]], ObsState.EMPTY, 3, 1)
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
        try:
            test_proxies.on()
                
            assert test_proxies.subarray[1].State() == DevState.ON
            assert test_proxies.subarray[1].obsState == ObsState.EMPTY

            input_receptors = [1, 4]

            # add some receptors and turn subarray off 
            test_proxies.subarray[1].AddReceptors(input_receptors)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.RESOURCING, 1, 1)
            test_proxies.subarray[1].Off()
            test_proxies.wait_timeout_dev([test_proxies.subarray[1]], DevState.OFF, 3, 1)
            assert test_proxies.subarray[1].State() == DevState.OFF
            assert len(test_proxies.subarray[1].receptors) == 0
            assert all([test_proxies.vcc[i + 1].subarrayMembership == 0 for i in range(test_proxies.num_vcc)])

            test_proxies.subarray[1].On()
            test_proxies.wait_timeout_dev([test_proxies.subarray[1]], DevState.ON, 3, 1)
            test_proxies.subarray[1].AddReceptors(input_receptors)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.IDLE, 1, 1)

            # end configuration with off command
            f = open(data_file_path + "Configure_TM-CSP_v2.json")
            configuration = f.read().replace("\n", "")
            f.close()
            test_proxies.subarray[1].ConfigureScan(configuration)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.CONFIGURING, 1, 1)
            test_proxies.subarray[1].Off()
            test_proxies.wait_timeout_dev([test_proxies.subarray[1]], DevState.OFF, 3, 1)
            assert test_proxies.subarray[1].State() == DevState.OFF
            assert len(test_proxies.subarray[1].receptors) == 0
            assert all([test_proxies.vcc[i + 1].subarrayMembership == 0 for i in range(test_proxies.num_vcc)])

            test_proxies.subarray[1].On()
            test_proxies.wait_timeout_dev([test_proxies.subarray[1]], DevState.ON, 3, 1)
            test_proxies.subarray[1].AddReceptors(input_receptors)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.IDLE, 1, 1)

            # end scan with off command
            f2 = open(data_file_path + "Scan2_basic.json")
            scan = f2.read().replace("\n", "")
            f2.close()
            test_proxies.subarray[1].ConfigureScan(configuration)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.READY, 5, 1)
            configuration = json.loads(configuration)
            # scan
            test_proxies.subarray[1].Scan(scan)
            test_proxies.wait_timeout_obs([test_proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert test_proxies.subarray[1].obsState == ObsState.SCANNING
            assert test_proxies.subarray[1].scanID == 2
            assert test_proxies.vcc[test_proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert test_proxies.vcc[test_proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("{}".format(fsp_id))
                # check configured attributes of FSP subarray
                #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                assert test_proxies.fspSubarray[fsp_id].obsState == ObsState.SCANNING
            test_proxies.subarray[1].Off()
            test_proxies.wait_timeout_dev([test_proxies.subarray[1]], DevState.OFF, 3, 1)
            assert test_proxies.subarray[1].scanID == 0
            assert test_proxies.subarray[1].State() == DevState.OFF
            assert len(test_proxies.subarray[1].receptors) == 0
            assert test_proxies.vcc[test_proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert test_proxies.vcc[test_proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE
            assert all([test_proxies.vcc[i + 1].subarrayMembership == 0 for i in range(test_proxies.num_vcc)])
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("{}".format(fsp_id))
                # check configured attributes of FSP subarray
                #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                assert test_proxies.fspSubarray[fsp_id].obsState == ObsState.IDLE

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
