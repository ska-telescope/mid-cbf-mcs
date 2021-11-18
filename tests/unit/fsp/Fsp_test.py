#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the Fsp."""

from __future__ import annotations
from typing import List

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict
from enum import Enum

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_tango_base.commands import ResultCode
from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState

class TestFsp:
    """
    Test class for CbfController tests.
    """

    def test_On_Off(
        self: TestFsp,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test for Fsp device.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """
    
        assert device_under_test.State() == DevState.OFF

        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        device_under_test.Off()
        time.sleep(3)
        assert device_under_test.State() == DevState.OFF
    
    @pytest.mark.parametrize(
        "sub_ids", 
        [
            (
                [3, 4, 15]
            ),
            (
                [1]
            )
        ]
    )
    def test_AddRemoveSubarrayMembership(
        self: TestFsp,
        device_under_test: CbfDeviceProxy,
        sub_ids: List[int]
    ) -> None:

        assert device_under_test.State() == DevState.OFF

        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON

        # subarray membership should be empty
        assert device_under_test.subarrayMembership == None

        # add fsp to all but last test subarray
        for sub_id in sub_ids[:-1]:
            device_under_test.AddSubarrayMembership(sub_id)
            time.sleep(3)
        for idx, sub_id in enumerate(sub_ids[:-1]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[:-1][idx]

        # remove fsp from first test subarray
        device_under_test.RemoveSubarrayMembership(sub_ids[0])
        time.sleep(3)
        for idx, sub_id in enumerate(sub_ids[1:-1]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[1:-1][idx]
        
        # add fsp to last test subarray
        device_under_test.AddSubarrayMembership(sub_ids[-1])
        time.sleep(3)
        for idx, sub_id in enumerate(sub_ids[1:]):
            assert device_under_test.read_attribute("subarrayMembership", \
                extract_as=tango.ExtractAs.List).value[idx] == sub_ids[1:][idx]
       
        # remove fsp from all subarrays
        for sub_id in sub_ids:
            device_under_test.RemoveSubarrayMembership(sub_id)
            time.sleep(3)
        assert device_under_test.subarrayMembership == None
    
    @pytest.mark.parametrize(
        "timing_beam_weights_file_name, \
         sub_id",
        [
            (
                "/../../data/timingbeamweights_fsp_unit_test.json",
                1
            )
        ]
    )
    def test_UpdateBeamWeights(
        self: TestFsp,
        device_under_test: CbfDeviceProxy,
        timing_beam_weights_file_name: str,
        sub_id: int
    ) -> None:

        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        device_under_test.AddSubarrayMembership(sub_id)
        time.sleep(3)
        assert device_under_test.read_attribute("subarrayMembership", \
            extract_as=tango.ExtractAs.List).value == [sub_id]

        # timing beam weights should be set to 0.0 after init
        num_cols = 6
        num_rows = 4
        assert device_under_test.read_attribute("timingBeamWeights", \
             extract_as=tango.ExtractAs.List).value == [[0.0] * num_cols for _ in range(num_rows)]

        # update only valid for function mode PST-BF
        device_under_test.SetFunctionMode("PST-BF")
        time.sleep(0.1)
        #TODO: this enum should be defined once and referred to throughout the project
        FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
        assert device_under_test.functionMode == FspModes.PST_BF.value

        # read the json file
        f = open(file_path + timing_beam_weights_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        timing_beam_weights = json.loads(json_str)
        
        # update the weights 
        for weights in timing_beam_weights["beamWeights"]:
            beam_weights_details = weights["beamWeightsDetails"]

            device_under_test.UpdateBeamWeights(json.dumps(beam_weights_details))

        time.sleep(3)
        # verify the weights were updated successfully 
        for weights in timing_beam_weights["beamWeights"]:
            beam_weights_details = weights["beamWeightsDetails"]
            for receptor in beam_weights_details:
                recptor_id = receptor["receptor"]
                for frequency_slice in receptor["receptorWeightsDetails"]:
                    weights = frequency_slice["weights"]
                    assert device_under_test.read_attribute("timingBeamWeights", \
                        extract_as=tango.ExtractAs.List).value[recptor_id -1] == weights
    
    @pytest.mark.parametrize(
        "jones_matrix_file_name, \
         sub_id",
        [
            (
                "/../../data/jonesmatrix_fsp_unit_test.json",
                1
            )
        ]
    )
    def test_UpdateJonesMatrix(
        self: TestFsp,
        device_under_test: CbfDeviceProxy,
        jones_matrix_file_name: str,
        sub_id: int
    ) -> None:

        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        device_under_test.AddSubarrayMembership(sub_id)
        time.sleep(3)
        assert device_under_test.read_attribute("subarrayMembership", \
            extract_as=tango.ExtractAs.List).value == [sub_id]

        # jones matrix values should be set to 0.0 after init
        num_cols = 4
        num_rows = 4
        assert device_under_test.read_attribute("jonesMatrix", \
             extract_as=tango.ExtractAs.List).value == [[0.0] * num_cols for _ in range(num_rows)]

        # update only valid for function mode PSS-BF
        device_under_test.SetFunctionMode("PSS-BF")
        time.sleep(0.1)
        FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
        assert device_under_test.functionMode == FspModes.PSS_BF.value

        # read the json file
        f = open(file_path + jones_matrix_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        jones_matrix = json.loads(json_str)

        # update the jones matrix
        for m in jones_matrix["jonesMatrix"]:
            if m["destinationType"] == "fsp":
                device_under_test.UpdateJonesMatrix(json.dumps(m["matrixDetails"]))
        
        time.sleep(3)
        # verify the jones matrix was updated successfully 
        for m in jones_matrix["jonesMatrix"]:
            if m["destinationType"] == "fsp":
                for matrixDetail in m["matrixDetails"]:
                    receptor_id = matrixDetail["receptor"]
                    for receptorMatrix in matrixDetail["receptorMatrix"]:
                        matrix = receptorMatrix["matrix"]
                        assert device_under_test.read_attribute("jonesMatrix", \
                            extract_as=tango.ExtractAs.List).value[receptor_id -1] == matrix
    
    @pytest.mark.parametrize(
        "delay_model_file_name, \
         sub_id",
        [
            (
                "/../../data/delaymodel_fsp_unit_test.json",
                1
            )
        ]
    )
    def test_UpdateDelayModel(
        self: TestFsp,
        device_under_test: CbfDeviceProxy,
        delay_model_file_name: str,
        sub_id: int
    ) -> None:

        assert device_under_test.State() == DevState.OFF
        device_under_test.On()
        time.sleep(3)
        assert device_under_test.State() == DevState.ON
        device_under_test.AddSubarrayMembership(sub_id)
        time.sleep(3)
        assert device_under_test.read_attribute("subarrayMembership", \
            extract_as=tango.ExtractAs.List).value == [sub_id]

        # delay model values should be set to 0.0 after init
        num_cols = 6
        num_rows = 4
        assert device_under_test.read_attribute("delayModel", \
             extract_as=tango.ExtractAs.List).value == [[0.0] * num_cols for _ in range(num_rows)]
        
        # read the json file
        f = open(file_path + delay_model_file_name)
        json_str = f.read().replace("\n", "")
        f.close()
        delay_model = json.loads(json_str)

        valid_function_modes = ["PSS-BF", "PST-BF"]
        for mode in valid_function_modes:
            device_under_test.SetFunctionMode(mode)
            time.sleep(0.1)
            FspModes = Enum('FspModes', 'CORR PSS_BF PST_BF VLBI')
            if mode == "PSS-BF":
                assert device_under_test.functionMode == FspModes.PSS_BF.value
            elif mode == "PST-BF":
                assert device_under_test.functionMode == FspModes.PST_BF.value

            # update the delay model
            for m in delay_model["delayModel"]:
                if m["destinationType"] == "fsp":
                    device_under_test.UpdateDelayModel(json.dumps(m["delayDetails"]))

            time.sleep(3)
            # verify the delay model was updated successfully 
            for m in delay_model["delayModel"]:
                if m["destinationType"] == "fsp":
                    for delayDetail in m["delayDetails"]:
                        receptor_id = delayDetail["receptor"]
                        for receptorDelayDetail in delayDetail["receptorDelayDetails"]:
                            delayCoeffs = receptorDelayDetail["delayCoeff"]
                            assert device_under_test.read_attribute("delayModel", \
                                extract_as=tango.ExtractAs.List).value[receptor_id -1] == delayCoeffs 

