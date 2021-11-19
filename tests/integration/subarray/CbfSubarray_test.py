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
        proxies: pytest.fixture, 
        receptor_ids: List[int], 
        receptors_to_remove: List[int], 
        sub_id: int
    ) -> None:
        """
        Test valid AddReceptors and RemoveReceptors commands
        """

        if proxies.debug_device_is_on:
            port = proxies.subarray[sub_id].DebugDevice()

        try:
            # controller will turn On/Off all of its subordinate devices,
            # including the subarrays, FSPs and VCCs
            proxies.on()

            assert proxies.subarray[sub_id].State() == DevState.ON
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 
                for i in range(len(proxies.vcc))])

            # add all except last receptor
            proxies.subarray[sub_id].AddReceptors(receptor_ids[:-1])
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert [proxies.subarray[sub_id].receptors[i] 
                for i in range(len(receptor_ids[:-1]))] == receptor_ids[:-1]
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == sub_id 
                for i in receptor_ids[:-1]])
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE

            # add the last receptor
            proxies.subarray[sub_id].AddReceptors([receptor_ids[-1]])
            time.sleep(1)
            assert [proxies.subarray[sub_id].receptors[i] 
                for i in range(len(receptor_ids))] == receptor_ids
            assert proxies.vcc[proxies.receptor_to_vcc[receptor_ids[-1]]].subarrayMembership == sub_id

            # remove all except last receptor
            proxies.subarray[sub_id].RemoveReceptors(receptors_to_remove)
            time.sleep(1)
            receptor_ids_after_remove = [r for r in receptor_ids if r not in receptors_to_remove]
            for idx, receptor in enumerate(receptor_ids_after_remove):
                assert proxies.subarray[sub_id].receptors[idx] == receptor
                assert proxies.vcc[proxies.receptor_to_vcc[receptor]].subarrayMembership == sub_id
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 0 
                for i in receptors_to_remove])

            # remove remaining receptor
            proxies.subarray[sub_id].RemoveReceptors(receptor_ids_after_remove)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
            assert len(proxies.subarray[sub_id].receptors) == 0
            for receptor in receptor_ids_after_remove:
                assert proxies.vcc[proxies.receptor_to_vcc[receptor]].subarrayMembership == 0
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
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
            proxies.on()
            
            assert proxies.subarray[sub_id].State() == DevState.ON
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])

            # add some receptors 
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert [proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try adding an invalid receptor ID
            result = proxies.subarray[sub_id].AddReceptors(invalid_receptor_id)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.FAULT, 1, 1)
            assert result[0][0] == ResultCode.FAILED
            assert [proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])

            proxies.subarray[sub_id].Restart()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)

            proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
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
            proxies.on()
            
            assert proxies.subarray[sub_id].State() == DevState.ON
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])

            # add some receptors 
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert [proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 1 for i in receptor_ids])
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE

            # try removing a receptor not assigned to subarray 1
            # doing this doesn't actually throw an error
            proxies.subarray[sub_id].RemoveReceptors(invalid_receptors_to_remove)
            assert [proxies.subarray[sub_id].receptors[i] for i in range(len(receptor_ids))] == receptor_ids
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)

            proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        receptor_ids: List[int], 
        sub_id: int
    ) -> None:
        """
        Test RemoveAllReceptors command
        """
        try:
            proxies.on()
            
            assert proxies.subarray[sub_id].State() == DevState.ON
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # receptor list should be empty right after initialization
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])

            # add some receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == sub_id for i in receptor_ids])
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE

            # remove all receptors
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert all([proxies.vcc[proxies.receptor_to_vcc[i]].subarrayMembership == 0 for i in receptor_ids])
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            proxies.off()
        
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        receptor_ids: List[int], 
        vcc_receptors: List[int],
    ) -> None:
        """
        Test a successful scan configuration
        """
        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])
            proxies.subarray[sub_id].loggingLevel = LoggingLevel.DEBUG

            # check initial value of attributes of CBF subarray
            vcc_index = proxies.receptor_to_vcc[4]
            
            logging.info("vcc_index  = {}".format( vcc_index ))

            assert len(proxies.subarray[sub_id].receptors) == 0
            assert proxies.subarray[sub_id].configID == ''
            # TODO in CbfSubarray, at end of scan, clear all private data
            #assert proxies.subarray[sub_id].frequencyBand == 0
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            #TODO currently only support for 1 receptor per fsp
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            # check configured attributes of CBF subarray
            assert sub_id == int(configuration["common"]["subarray_id"])
            assert proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            band_index = freq_band_dict()[configuration["common"]["frequency_band"]]
            assert band_index == proxies.subarray[sub_id].frequencyBand 
            assert proxies.subarray[sub_id].obsState == ObsState.READY

            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.READY, 1, 1)

            # check the rest of the configured attributes of VCCs

            #TODO fix these tests; issue with VccBand devices either not reconfiguring in between
            #     configurations or causing a fault within the Vcc device
            # assert [proxy.State() for proxy in proxies.vccBand[proxies.receptor_to_vcc[4] - 1]] == [
            #     DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]
            # assert [proxy.State() for proxy in proxies.vccBand[proxies.receptor_to_vcc[1] - 1]] == [
            #     DevState.DISABLE, DevState.DISABLE, DevState.DISABLE, DevState.ON]

            # check the rest of the configured attributes of VCCs
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].frequencyBand == band_index
                assert proxies.vcc[proxies.receptor_to_vcc[r]].subarrayMembership == sub_id
                assert proxies.vcc[proxies.receptor_to_vcc[r]].configID == configuration["common"]["config_id"]
                if "band_5_tuning" in configuration["common"]:
                    for idx, band in enumerate(configuration["common"]["band_5_tuning"]):
                        assert proxies.vcc[proxies.receptor_to_vcc[r]].band5Tuning[idx] == band
                if "frequency_band_offset_stream_1" in configuration["cbf"]: 
                        assert proxies.vcc[proxies.receptor_to_vcc[r]].frequencyBandOffsetStream1 \
                            == configuration["cbf"]["frequency_band_offset_stream_1"]
                if "frequency_band_offset_stream_2" in configuration["cbf"]:
                        assert proxies.vcc[proxies.receptor_to_vcc[r]].frequencyBandOffsetStream2 \
                            == configuration["cbf"]["frequency_band_offset_stream_2"]
                if "rfi_flagging_mask" in configuration["cbf"]: 
                    assert proxies.vcc[proxies.receptor_to_vcc[r]].rfiFlaggingMask \
                        == str(configuration["cbf"]["rfi_flagging_mask"])
            
            # check configured attributes of search windows
            # first for search window 1...
            
            # TODO - SearchWidow device test is disabled since the same 
            # functionality is implemented by the VccSearchWindow device; 
            # to be decide which one to keep.

            # print("proxies.sw[1].State() = {}".format(proxies.sw[1].State()))
            # print("proxies.sw[2].State() = {}".format(proxies.sw[2].State()))

            # assert proxies.sw[1].State() == DevState.ON
            # assert proxies.sw[1].searchWindowTuning == 6000000000
            # assert proxies.sw[1].tdcEnable == True
            # assert proxies.sw[1].tdcNumBits == 8
            # assert proxies.sw[1].tdcPeriodBeforeEpoch == 5
            # assert proxies.sw[1].tdcPeriodAfterEpoch == 25
            # assert "".join(proxies.sw[1].tdcDestinationAddress.split()) in [
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"receptorID\":1,\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"]}]",
            #     "[{\"receptorID\":4,\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"]},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            #     "[{\"tdcDestinationAddress\":[\"foo\",\"bar\",\"8080\"],\"receptorID\":4},{\"tdcDestinationAddress\":[\"fizz\",\"buzz\",\"80\"],\"receptorID\":1}]",
            # ]
            # # then for search window 2...
            # assert proxies.sw[2].State() == DevState.DISABLE
            # assert proxies.sw[2].searchWindowTuning == 7000000000
            # assert proxies.sw[2].tdcEnable == False

            time.sleep(1)
            # check configured attributes of VCC search windows
            if "search_window" in configuration["cbf"]:
                for idx, search_window in enumerate(configuration["cbf"]["search_window"]):
                    for r in vcc_receptors:
                        assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].tdcEnable == search_window["tdc_enable"]
                        if search_window["tdc_enable"]:
                            assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].State() == DevState.ON
                        else:
                            assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].State() == DevState.DISABLE
                        assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].searchWindowTuning == search_window["search_window_tuning"]
                        if "tdc_num_bits" in search_window:
                            assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].tdcNumBits == search_window["tdc_num_bits"]
                        if "tdc_period_before_epoch" in search_window:
                            assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].tdcPeriodBeforeEpoch == search_window["tdc_period_before_epoch"]
                        if "tdc_period_after_epoch" in search_window:
                            assert proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].tdcPeriodAfterEpoch == search_window["tdc_period_after_epoch"]
                        if "tdc_destination_address" in search_window:
                            tdcDestAddr = [t["tdc_destination_address"] for t in search_window["tdc_destination_address"] if t["receptor_id"] == r]
                            assert [list(proxies.vccTdc[proxies.receptor_to_vcc[r] - 1][idx].tdcDestinationAddress)] == tdcDestAddr
 
           # check configured attributes of FSPs, including states of function mode capabilities
            fsp_function_mode_proxies = [proxies.fsp1FunctionMode, proxies.fsp2FunctionMode, 
                                         proxies.fsp3FunctionMode, proxies.fsp4FunctionMode]
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("Check for fsp id = {}".format(fsp_id))

                if fsp["function_mode"] == "CORR": 
                    function_mode = FspModes.CORR.value
                    assert proxies.fsp[fsp_id].functionMode == function_mode
                    assert sub_id in proxies.fsp[fsp_id].subarrayMembership
                    assert [proxy.State() for proxy in fsp_function_mode_proxies[fsp_id-1]] == [
                        DevState.ON, DevState.DISABLE, DevState.DISABLE, DevState.DISABLE
                    ]
                    # check configured attributes of FSP subarray
                    #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                    assert proxies.fspSubarray[fsp_id].obsState == ObsState.READY
                    # currently only support for one receptor so only index 0 is checked
                    if "receptor_ids" in fsp:
                        assert proxies.fspSubarray[fsp_id].receptors == fsp["receptor_ids"][0]
                    else:
                        assert proxies.fspSubarray[fsp_id].receptors == receptor_ids[0]
                    assert proxies.fspSubarray[fsp_id].frequencyBand == band_index
                    if "band_5_tuning" in configuration["common"]:
                        for idx, band in enumerate(configuration["common"]["band_5_tuning"]):
                            assert proxies.fspSubarray[fsp_id].band5Tuning[idx] == band
                    if "frequency_band_offset_stream_1" in configuration["cbf"]:
                        assert proxies.fspSubarray[fsp_id].frequencyBandOffsetStream1 == configuration["cbf"]["frequency_band_offset_stream_1"]
                    if "frequency_band_offset_stream_2" in configuration["cbf"]:
                        assert proxies.fspSubarray[fsp_id].frequencyBandOffsetStream2 == configuration["cbf"]["frequency_band_offset_stream_2"]                   
                    assert proxies.fspSubarray[fsp_id].frequencySliceID == fsp["frequency_slice_id"]
                    assert proxies.fspSubarray[fsp_id].integrationTime == fsp["integration_factor"]
                    assert proxies.fspSubarray[fsp_id].corrBandwidth == fsp["zoom_factor"]
                    if fsp["zoom_factor"] > 0:
                        assert proxies.fspSubarray[fsp_id].zoomWindowTuning == fsp["zoom_window_tuning"]
                    assert proxies.fspSubarray[fsp_id].fspChannelOffset == fsp["channel_offset"]

                    for i in range(len(fsp["channel_averaging_map"])):
                        for j in range(len(fsp["channel_averaging_map"][i])):
                            assert proxies.fspSubarray[fsp_id].channelAveragingMap[i][j] == fsp["channel_averaging_map"][i][j]

                    for i in range(len(fsp["output_link_map"])):
                        for j in range(len(fsp["output_link_map"][i])):
                            assert proxies.fspSubarray[fsp_id].outputLinkMap[i][j] == fsp["output_link_map"][i][j]
                    
                    if "output_host" and "output_mac" and "output_port" in fsp:
                        assert str(proxies.fspSubarray[sub_id].visDestinationAddress).replace('"',"'") == \
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
                    assert proxies.fsp[fsp_id].functionMode == function_mode
                    assert proxies.fspSubarray[fsp_id].searchWindowID == fsp["search_window_id"]

                    # TODO: currently searchBeams is stored by the device
                    #       as a json string ( via attribute 'searchBeams');  
                    #       this has to be updated in FspPssSubarray
                    #       to read/write individual members
                    for idx, sBeam in enumerate(proxies.fspSubarray[fsp_id].searchBeams):
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
                    assert proxies.fsp[fsp_id].functionMode == function_mode

                    assert proxies.fsp[fsp_id].State() == DevState.ON
                    assert sub_id in proxies.fsp[fsp_id].subarrayMembership
                    assert [proxy.State() for proxy in proxies.fsp2FunctionMode] == [
                        DevState.DISABLE, DevState.DISABLE, DevState.ON, DevState.DISABLE
                    ]
                    #TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_pst_id 5 = pst _01_01
                    # fsp_pst_id 6 = pst _02_01
                    fsp_pst_id = fsp_id + 4
                    assert proxies.fspSubarray[fsp_pst_id].obsState == ObsState.READY
                    for beam in fsp["timing_beam"]:
                        assert all([proxies.fspSubarray[fsp_pst_id].receptors[i] == j for i, j in zip(range(1), beam["receptor_ids"])])
                        assert all([proxies.fspSubarray[fsp_pst_id].timingBeamID[i] == j for i, j in zip(range(1), [beam["timing_beam_id"]])])

                elif fsp["function_mode"] == "VLBI": 
                    function_mode = FspModes.VLBI.value
                    assert proxies.fsp[fsp_id].functionMode == function_mode
                    #TODO: This mode is not tested

            # Clean Up
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.off()
        
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
    def test_ConfigureScan_onlyPst_basic_FSP_scan_parameters(
        self: TestCbfSubarray, 
        proxies: pytest.fixture, 
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
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            # check initial value of attributes of CBF subarray
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert proxies.subarray[sub_id].configID == ''
            assert proxies.subarray[sub_id].frequencyBand == 0
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            
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
            proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(5)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range( len(jones_matrix_index_per_epoch) ):

                for receptor in jones_matrix["jonesMatrix"][jones_matrix_index_per_epoch[epoch]]["matrixDetails"]:
                    rec_id = receptor["receptor"]
                    for fsp in [proxies.fsp[i + 1] for i in range(len(proxies.fsp))]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value, FspModes.VLBI.value]:
                            for frequency_slice in receptor["receptorMatrix"]:
                                if fsp.functionMode == FspModes.PSS_BF.value:
                                    proxy_subarray = proxies.fspPssSubarray[sub_id -1]
                                    fs_length = 16
                                elif fsp.functionMode == FspModes.PST_BF.value:
                                    proxy_subarray = proxies.fspPstSubarray[sub_id -1]
                                    fs_length = 4
                                else:
                                    fs_length = 4
                                    log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                                    logging.error(log_msg)
                                if rec_id in proxy_subarray.receptors:
                                    fs_id = frequency_slice["fsid"]
                                    if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                        matrix = frequency_slice["matrix"]
                                        if len(matrix) == fs_length:
                                            for idx, matrix_val in enumerate(matrix):
                                                assert matrix_val == fsp.jonesMatrix[rec_id -1][idx]                                                                               

                time.sleep(10)

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
            proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(5)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range( len(delay_model_index_per_epoch) ):

                model = delay_model["delayModel"][delay_model_index_per_epoch[epoch]]            
                for delayDetail in model["delayDetails"]:
                    for fsp in [proxies.fsp[i + 1] for i in range(len(proxies.fsp))]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                rec_id = delayDetail["receptor"]
                                if fsp.functionMode == FspModes.PSS_BF.value:
                                    proxy_subarray = proxies.fspPssSubarray[sub_id -1]
                                else:
                                    proxy_subarray = proxies.fspPstSubarray[sub_id -1]
                                if rec_id in proxy_subarray.receptors:
                                    fs_id = receptorDelayDetail["fsid"]
                                    if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                        delayCoeff = receptorDelayDetail["delayCoeff"]
                                        for idx, coeff in enumerate(delayCoeff):
                                            assert coeff == fsp.delayModel[rec_id -1][idx]                                           

                time.sleep(10)

            # update timing beam weights from tm emulator
            f = open(data_file_path + timing_beam_weights_file_name)
            timing_beam_weights = json.loads(f.read().replace("\n", ""))
            epoch = str(int(time.time()))
            for weights in timing_beam_weights["beamWeights"]:
                weights["epoch"] = epoch
                epoch = str(int(epoch) + 10)
            
            # update delay model
            proxies.tm.beamWeights = json.dumps(timing_beam_weights)
            time.sleep(1)

            for weights in timing_beam_weights["beamWeights"]:
                for receptor in weights["beamWeightsDetails"]:
                    rec_id = int(receptor["receptor"])
                    fs_id = receptor["receptorWeightsDetails"][0]["fsid"]
                    for index, value in enumerate(receptor["receptorWeightsDetails"][0]["weights"]):
                        try:
                            assert proxies.fsp[fs_id].timingBeamWeights[rec_id - 1][index] == value
                        except AssertionError as ae:
                            raise ae
                        except Exception as e:
                            raise e
                time.sleep(10)

            # Clean Up
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.off()
        
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the EndScan command
        """

        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            num_receptors = len(receptor_ids)

            vcc_ids = [None for _ in range(num_receptors)]
            for receptor_id, ii in zip(receptor_ids, range(num_receptors)):
                vcc_ids[ii] = proxies.receptor_to_vcc[receptor_id]

            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(num_receptors), receptor_ids)])
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE

            # Check fsp obsState BEFORE scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE

            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            # check some configured attributes of CBF subarray           
            frequency_band   = configuration["common"]["frequency_band"]
            input_band_index = freq_band_dict()[frequency_band]

            assert proxies.subarray[sub_id].configID == configuration["common"]["config_id"]
            assert proxies.subarray[sub_id].frequencyBand == input_band_index
            assert proxies.subarray[sub_id].obsState == ObsState.READY

            # Check fsp obsState AFTER scan configuration:
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    # TODO: improve indexing by changing the 1D array to a 2D array  
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY

            # Send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string = f2.read().replace("\n", "")
            proxies.subarray[sub_id].Scan(json_string)
            f2.close()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)

            # Check obsStates BEFORE the EndScan() command
            assert proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert proxies.vcc[vcc_ids[0]].obsState == ObsState.SCANNING
            assert proxies.vcc[vcc_ids[num_receptors-1]].obsState == ObsState.SCANNING

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.SCANNING

            proxies.subarray[sub_id].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 1, 1)

            # Check obsStates AFTER the EndScan() command
            assert proxies.subarray[sub_id].obsState  == ObsState.READY
            assert proxies.vcc[vcc_ids[0]].obsState  == ObsState.READY
            assert proxies.vcc[vcc_ids[num_receptors -1]].obsState == ObsState.READY
            # assert proxies.fspCorrSubarray[fsp_corr_id-1].obsState == ObsState.READY
            # assert proxies.fspPssSubarray[fsp_pss_id-1].obsState == ObsState.READY
            # assert proxies.fspPstSubarray[fsp_pst_id-1].obsState == ObsState.READY

            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY

            # Clean up
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.on()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
    def test_ConfigureScan_delayModel(
        self: TestCbfSubarray, 
        proxies: pytest.fixture, 
        config_file_name: str,
        delay_model_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int],
    ) -> None:

        """
        Test the reception of delay models
        """
        
        # Read delay model data from file
        f = open(data_file_path + delay_model_file_name)
        json_string_delay_mod = f.read().replace("\n", "")
        delay_model = json.loads(json_string_delay_mod)
        f.close()

        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)
            sub_id = int(configuration["common"]["subarray_id"])

            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            assert proxies.subarray[sub_id].obsState == ObsState.READY
            
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
            proxies.tm.delayModel = json.dumps(delay_model)
            time.sleep(5)

            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            epoch_to_scan = 1
            num_cols = 6
            num_rows_vcc = 26

            for epoch in range( len(delay_model_index_per_epoch) ):

                model = delay_model["delayModel"][delay_model_index_per_epoch[epoch]]            
                for delayDetail in model["delayDetails"]:
                    for r in vcc_receptors:
                        vcc = proxies.vcc[proxies.receptor_to_vcc[r]]  
                        if delayDetail["receptor"] == r:
                            mod_vcc = [[0.0] * num_cols for i in range(num_rows_vcc)]
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                fs_id = receptorDelayDetail["fsid"]
                                delayCoeff = receptorDelayDetail["delayCoeff"]
                                mod_vcc[fs_id -1] = delayCoeff
                            for i in range(len(mod_vcc)):
                                for j in range(len(mod_vcc[i])):
                                    assert vcc.delayModel[i][j] == mod_vcc[i][j]
                    for fsp in [proxies.fsp[i + 1] for i in range(len(proxies.fsp))]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value]:
                            for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                                rec_id = delayDetail["receptor"]
                                if fsp.functionMode == FspModes.PSS_BF.value:
                                    proxy_subarray = proxies.fspPssSubarray[sub_id -1]
                                else:
                                    proxy_subarray = proxies.fspPstSubarray[sub_id -1]
                                if rec_id in proxy_subarray.receptors:
                                    fs_id = receptorDelayDetail["fsid"]
                                    if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                        delayCoeff = receptorDelayDetail["delayCoeff"]
                                        for idx, coeff in enumerate(delayCoeff):
                                            assert coeff == fsp.delayModel[rec_id -1][idx]                                           
                              
                if epoch == epoch_to_scan:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    proxies.subarray[sub_id].Scan(f2.read().replace("\n", ""))
                    f2.close()
                    proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
                    assert proxies.subarray[sub_id].obsState == ObsState.SCANNING

                time.sleep(10)

            # Clean up
            proxies.subarray[sub_id].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        jones_matrix_file_name: str,
        receptor_ids: List[int]
    ) -> None:
        """
        Test the reception of Jones matrices
        """
        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                       for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)

            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            assert proxies.subarray[sub_id].obsState == ObsState.READY

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
            proxies.tm.jonesMatrix = json.dumps(jones_matrix)
            time.sleep(5)

            epoch_to_scan = 1
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')

            for epoch in range( len(jones_matrix_index_per_epoch) ):

                for receptor in jones_matrix["jonesMatrix"][jones_matrix_index_per_epoch[epoch]]["matrixDetails"]:
                    for frequency_slice in receptor["receptorMatrix"]:
                        for index, value in enumerate(frequency_slice["matrix"]):
                            vcc_id = proxies.receptor_to_vcc[receptor["receptor"]]
                            fs_id = frequency_slice["fsid"]
                            try:
                                assert proxies.vcc[vcc_id].jonesMatrix[fs_id-1][index] == value
                            except AssertionError as ae:
                                logging.error(
                                    "AssertionError; incorrect Jones matrix entry: \
                                    epoch {}, VCC {}, i = {}, jonesMatrix[{}] = {}".format
                                        (
                                            jones_matrix["jonesMatrix"][1]["epoch"], 
                                            vcc_id, index, 
                                            fs_id-1, 
                                            proxies.vcc[vcc_id].jonesMatrix[fs_id-1]
                                        )
                                )
                                raise ae
                            except Exception as e:
                                raise e  
                    rec_id = receptor["receptor"]
                    for fsp in [proxies.fsp[i + 1] for i in range(len(proxies.fsp))]:
                        if fsp.functionMode in [FspModes.PSS_BF.value, FspModes.PST_BF.value, FspModes.VLBI.value]:
                            for frequency_slice in receptor["receptorMatrix"]:
                                if fsp.functionMode == FspModes.PSS_BF.value:
                                    proxy_subarray = proxies.fspPssSubarray[sub_id -1]
                                    fs_length = 16
                                elif fsp.functionMode == FspModes.PST_BF.value:
                                    proxy_subarray = proxies.fspPstSubarray[sub_id -1]
                                    fs_length = 4
                                else:
                                    fs_length = 4
                                    log_msg = "function mode {} currently not supported".format(fsp.functionMode)
                                    logging.error(log_msg)
                                if rec_id in proxy_subarray.receptors:
                                    fs_id = frequency_slice["fsid"]
                                    if fs_id == int(fsp.get_property("FspID")['FspID'][0]):
                                        matrix = frequency_slice["matrix"]
                                        if len(matrix) == fs_length:
                                            for idx, matrix_val in enumerate(matrix):
                                                assert matrix_val == fsp.jonesMatrix[rec_id -1][idx]                                                   
                              
                if epoch == epoch_to_scan:
                    # transition to obsState=SCANNING
                    f2 = open(data_file_path + scan_file_name)
                    proxies.subarray[sub_id].Scan(f2.read().replace("\n", ""))
                    f2.close()
                    proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
                    assert proxies.subarray[sub_id].obsState == ObsState.SCANNING

                time.sleep(10)

            # Clean up
            proxies.subarray[sub_id].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.off()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test the Scan command
        """
        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY

            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])

            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)

            # check initial states
            assert proxies.subarray[sub_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY

            # send the Scan command
            f2 = open(data_file_path + scan_file_name)
            json_string_scan = f2.read().replace("\n", "")
            proxies.subarray[sub_id].Scan(json_string_scan)
            f2.close()
            scan_configuration = json.loads(json_string_scan)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            
            scan_id = scan_configuration["scan_id"]

            # check scanID on VCC and FSP
            assert proxies.fspSubarray[sub_id].scanID == scan_id
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].scanID == scan_id

            # check states
            assert proxies.subarray[sub_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.SCANNING

            # Clean up
            proxies.subarray[sub_id].EndScan()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 1, 1)
            proxies.subarray[sub_id].GoToIdle()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.IDLE, 3, 1)
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.on()

        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test abort reset
        """
        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":
                    # TODO: improve indexing by changing the 1D array to a 2D array  
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.READY
            # abort
            proxies.subarray[sub_id].Abort()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[sub_id].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert all([proxies.subarray[sub_id].receptors[i] == j for i, j in zip(range(3), receptor_ids)])
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert all([proxies.subarray[sub_id].receptors[i] == j 
                for i, j in zip(range(len(receptor_ids)), receptor_ids)])
            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert proxies.subarray[sub_id].scanID == scan_configuration["scan_id"]
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING

            # abort
            proxies.subarray[sub_id].Abort()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.ABORTED
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # ObsReset
            proxies.subarray[sub_id].ObsReset()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE
            assert proxies.subarray[sub_id].scanID == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

            # Clean up
            proxies.subarray[sub_id].RemoveAllReceptors()
            proxies.wait_timeout_obs([proxies.vcc[i + 1] for i in range(len(proxies.vcc))], ObsState.EMPTY, 3, 1)

            proxies.off()
        
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
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
        proxies: pytest.fixture, 
        config_file_name: str,
        scan_file_name: str,
        receptor_ids: List[int],
        vcc_receptors: List[int]
    ) -> None:
        """
        Test abort restart
        """
        try:
            proxies.on()
            
            f = open(data_file_path + config_file_name)
            json_string = f.read().replace("\n", "")
            f.close()
            configuration = json.loads(json_string)

            sub_id = int(configuration["common"]["subarray_id"])

            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            
            ############################# abort from IDLE ###########################
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.IDLE
            # abort
            proxies.subarray[sub_id].Abort()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # Restart: receptors should be empty
            proxies.subarray[sub_id].Restart()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(proxies.subarray[sub_id].receptors) == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE


            ############################# abort from READY ###########################
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.READY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # abort
            proxies.subarray[sub_id].Abort()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.ABORTED
            # ObsReset
            proxies.subarray[sub_id].Restart()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            assert len(proxies.subarray[sub_id].receptors) == 0
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE


            ############################# abort from SCANNING ###########################
            # add receptors
            proxies.subarray[sub_id].AddReceptors(receptor_ids)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.IDLE, 1, 1)
            # configure scan
            proxies.subarray[sub_id].ConfigureScan(json_string)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.READY, 5, 1)
            # scan
            f = open(data_file_path + scan_file_name)
            json_string_scan = f.read().replace("\n", "")
            proxies.subarray[sub_id].Scan(json_string_scan)
            f.close()
            scan_configuration = json.loads(json_string_scan)
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.SCANNING
            assert proxies.subarray[sub_id].scanID == scan_configuration["scan_id"]
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.SCANNING
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.SCANNING
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.SCANNING

            # abort
            proxies.subarray[sub_id].Abort()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.ABORTED, 1, 1)
            assert proxies.subarray[sub_id].obsState == ObsState.ABORTED
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR": 
                    # TODO: improve indexing by changing the 1D array to a 2D array 
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.READY
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.READY
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.READY
            for r in vcc_receptors:
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.READY

            # ObsReset
            proxies.subarray[sub_id].Restart()
            proxies.wait_timeout_obs([proxies.subarray[sub_id]], ObsState.EMPTY, 3, 1)
            assert len(proxies.subarray[sub_id].receptors) == 0
            assert proxies.subarray[sub_id].obsState == ObsState.EMPTY
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = int(fsp["fsp_id"])
                if fsp["function_mode"] == "CORR":  
                    # TODO: improve indexing by changing the 1D array to a 2D array
                    # fsp_corr_id 0 = mid_csp_cbf/fspCorrSubarray/_01_01
                    # fsp_corr_id 1 = mid_csp_cbf/fspCorrSubarray/_02_01
                    fsp_corr_id = fsp_id -1 
                    assert proxies.fspCorrSubarray[fsp_corr_id ].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PSS-BF":
                    # fsp_pss_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_03_01
                    # fsp_pss_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_04_01
                    fsp_pss_id = fsp_id - 3
                    assert proxies.fspPssSubarray[fsp_pss_id].obsState == ObsState.IDLE
                elif fsp["function_mode"] == "PST-BF":
                    # fsp_pst_id 0 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_01_01
                    # fsp_pst_id 1 = mid_csp_cbf/mid_csp_cbf/fspPssSubarray/_02_01
                    fsp_pst_id = fsp_id -1
                    assert proxies.fspPstSubarray[fsp_pst_id].obsState == ObsState.IDLE
            for r in vcc_receptors  :
                assert proxies.vcc[proxies.receptor_to_vcc[r]].obsState == ObsState.IDLE

            proxies.off()
        
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise e
    
    #TODO: remove entirely?
    @pytest.mark.skip(
        reason="OffCommand will not be invoked in this manner by CSP LMC Mid, \
        rather a series of commands will be issued (Abort -> Restart/Reset)"
    )
    def test_Abort_from_Resourcing(self, proxies):
        try:
            proxies.on()
                
            assert proxies.subarray[1].State() == DevState.ON
            assert proxies.subarray[1].obsState == ObsState.EMPTY

            input_receptors = [1, 4]

            # add some receptors and turn subarray off 
            proxies.subarray[1].AddReceptors(input_receptors)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.RESOURCING, 1, 1)
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)
            assert proxies.subarray[1].State() == DevState.OFF
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])

            proxies.subarray[1].On()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
            proxies.subarray[1].AddReceptors(input_receptors)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)

            # end configuration with off command
            f = open(data_file_path + "Configure_TM-CSP_v2.json")
            configuration = f.read().replace("\n", "")
            f.close()
            proxies.subarray[1].ConfigureScan(configuration)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.CONFIGURING, 1, 1)
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)
            assert proxies.subarray[1].State() == DevState.OFF
            assert len(proxies.subarray[1].receptors) == 0
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])

            proxies.subarray[1].On()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.ON, 3, 1)
            proxies.subarray[1].AddReceptors(input_receptors)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.IDLE, 1, 1)

            # end scan with off command
            f2 = open(data_file_path + "Scan2_basic.json")
            scan = f2.read().replace("\n", "")
            f2.close()
            proxies.subarray[1].ConfigureScan(configuration)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.READY, 5, 1)
            configuration = json.loads(configuration)
            # scan
            proxies.subarray[1].Scan(scan)
            proxies.wait_timeout_obs([proxies.subarray[1]], ObsState.SCANNING, 1, 1)
            assert proxies.subarray[1].obsState == ObsState.SCANNING
            assert proxies.subarray[1].scanID == 2
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.SCANNING
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.SCANNING
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("{}".format(fsp_id))
                # check configured attributes of FSP subarray
                #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                assert proxies.fspSubarray[fsp_id].obsState == ObsState.SCANNING
            proxies.subarray[1].Off()
            proxies.wait_timeout_dev([proxies.subarray[1]], DevState.OFF, 3, 1)
            assert proxies.subarray[1].scanID == 0
            assert proxies.subarray[1].State() == DevState.OFF
            assert len(proxies.subarray[1].receptors) == 0
            assert proxies.vcc[proxies.receptor_to_vcc[1]].obsState == ObsState.IDLE
            assert proxies.vcc[proxies.receptor_to_vcc[4]].obsState == ObsState.IDLE
            assert all([proxies.vcc[i + 1].subarrayMembership == 0 for i in range(len(proxies.vcc))])
            for fsp in configuration["cbf"]["fsp"]:
                fsp_id = fsp["fsp_id"]
                logging.info("{}".format(fsp_id))
                # check configured attributes of FSP subarray
                #TODO align IDs of fspSubarrays to fsp_id in conftest; currently works for fsps 1 and 2
                assert proxies.fspSubarray[fsp_id].obsState == ObsState.IDLE

            proxies.off()
            
            
        except AssertionError as ae:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise ae
        except Exception as e:
            time.sleep(2)
            proxies.clean_proxies()
            time.sleep(2)
            raise e
