#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the FspCorrSubarray."""

from __future__ import annotations

# Standard imports
import os
import time
import json
import logging
import pytest
from typing import Callable, Type, Dict

from ska_mid_cbf_mcs.device_proxy import CbfDeviceProxy

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
from tango.server import command

#SKA imports
from ska_mid_cbf_mcs.testing.tango_harness import DeviceToLoadType

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestFspCorrSubarray:
    """
    Test class for FspCorrSubarray tests.
    """

    # def test_AddRemoveReceptors_valid(
    #     self,
    #     tango_harness,
    #     device_under_test
    # ):
    #     """
    #     Test valid AddReceptors and RemoveReceptors commands
    #     """

        # mock_cbf_controller = tango_harness.get_device("mid_csp_cbf/sub_elt/controller")
        # mock_vcc = tango_harness.get_device("mid_csp_cbf/vcc/001")
        # mock_cbf_subarray_1 = tango_harness.get_device("mid_csp_cbf/sub_elt/subarray_01")
        # mock_fsp_pss_subarray_2_1 = tango_harness.get_device("mid_csp_cbf/fspPssSubarray/02_01")

    #     device_under_test.Init()
    #     mock_fsp_pss_subarray_2_1.Init()
    #     mock_cbf_subarray_1.Init()
    #     mock_vcc.Init()
    #     # for proxy in mock_vcc:
    #     #     proxy.Init()

    #     time.sleep(3)

    #     # receptor list should be empty right after initialization
    #     assert mock_cbf_subarray_1.receptors == ()
    #     assert device_under_test.receptors == ()
    #     assert mock_fsp_pss_subarray_2_1.receptors == ()

    #     # add some receptors
    #     mock_cbf_subarray_1.AddReceptors([1, 10, 197])
    #     time.sleep(1)
    #     assert mock_cbf_subarray_1.receptors == (1, 10, 197)
    #     device_under_test.AddReceptors([1, 10])
    #     mock_fsp_pss_subarray_2_1.AddReceptors([2, 9])
    #     assert device_under_test.receptors[0] == 1
    #     assert device_under_test.receptors[1] == 10
    #     assert mock_fsp_pss_subarray_2_1.receptors[0] == 2
    #     assert mock_fsp_pss_subarray_2_1.receptors[1] == 9

    #     # add more receptors
    #     device_under_test.AddReceptors([197])
    #     assert device_under_test.receptors[2] == 197

    #     # remove some receptors
    #     device_under_test.RemoveReceptors([10, 197])
    #     mock_fsp_pss_subarray_2_1.RemoveReceptors([2, 9])
    #     assert device_under_test.receptors[0] == 1

    #     # remove remaining receptors
    #     device_under_test.RemoveReceptors([1])
    #     assert device_under_test.receptors == ()
    #     assert mock_fsp_pss_subarray_2_1.receptors == ()

    # def test_AddRemoveReceptors_invalid(
    #         self,
    #         create_vcc_proxies,
    #         create_cbf_controller_proxy,
    #         create_cbf_subarray_1_proxy,
    #         create_fsp_corr_subarray_1_1_proxy,
    #         create_fsp_pss_subarray_2_1_proxy
    # ):
    #     """
    #     Test invalid AddReceptors and RemoveReceptors commands:
    #         - when a receptor to be added is not in use by the subarray
    #         - when a receptor ID is invalid (e.g. out of range)
    #         - when a receptor to be removed is not assigned to the subarray
    #     """
    #     create_fsp_corr_subarray_1_1_proxy.Init()
    #     create_fsp_pss_subarray_2_1_proxy.Init()
    #     create_cbf_subarray_1_proxy.Init()
    #     for proxy in create_vcc_proxies:
    #         proxy.Init()
    #     receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
    #                            create_cbf_controller_proxy.receptorToVcc)

    #     time.sleep(3)

    #     # receptor list should be empty right after initialization
    #     assert create_cbf_subarray_1_proxy.receptors == ()
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors == ()
    #     assert create_fsp_pss_subarray_2_1_proxy.receptors == ()

    #     # add some receptors
    #     create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
    #     time.sleep(1)
    #     assert create_cbf_subarray_1_proxy.receptors == (1, 10, 197)
    #     create_fsp_corr_subarray_1_1_proxy.AddReceptors([1, 10])
    #     create_fsp_pss_subarray_2_1_proxy.AddReceptors([2, 9])
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10
    #     assert create_fsp_pss_subarray_2_1_proxy.receptors[0] == 2
    #     assert create_fsp_pss_subarray_2_1_proxy.receptors[1] == 9

    #     # try adding a receptor not in use by the subarray
    #     assert create_vcc_proxies[receptor_to_vcc[17] - 1].subarrayMembership == 0
    #     with pytest.raises(tango.DevFailed) as df:
    #         create_fsp_corr_subarray_1_1_proxy.AddReceptors([17])
    #     assert "does not belong" in str(df.value.args[0].desc)
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

    #     # try adding an invalid receptor ID
    #     with pytest.raises(tango.DevFailed) as df:
    #         create_fsp_corr_subarray_1_1_proxy.AddReceptors([200])
    #     time.sleep(1)
    #     assert "Invalid receptor ID" in str(df.value.args[0].desc)

    #     # try removing a receptor not assigned to subarray 2
    #     # doing this doesn't actually throw an error
    #     create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([5])
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

    #     # remove all receptors
    #     create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([1, 10])
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

    # def test_RemoveAllReceptors(
    #         self,
    #         create_vcc_proxies,
    #         create_cbf_subarray_1_proxy,
    #         create_fsp_corr_subarray_1_1_proxy
    # ):
    #     """
    #     Test RemoveAllReceptors command
    #     """
    #     create_fsp_corr_subarray_1_1_proxy.Init()
    #     create_cbf_subarray_1_proxy.Init()
    #     for proxy in create_vcc_proxies:
    #         proxy.Init()

    #     time.sleep(3)

    #     # receptor list should be empty right after initialization
    #     assert create_cbf_subarray_1_proxy.receptors == ()
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

    #     # add some receptors
    #     create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
    #     time.sleep(1)
    #     assert create_cbf_subarray_1_proxy.receptors == (1, 10, 197)
    #     create_fsp_corr_subarray_1_1_proxy.AddReceptors([1, 10])
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

    #     # remove all receptors
    #     create_fsp_corr_subarray_1_1_proxy.RemoveAllReceptors()
    #     assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

    #FIXME
    def test_ConfigureScan_basic(
        self: TestFspCorrSubarray,
        device_under_test: CbfDeviceProxy
    ) -> None:
        """
        Test a minimal successful scan configuration.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the device under test, in a
            :py:class:`tango.test_context.DeviceTestContext`.
        """

        # mock_cbf_controller = tango_harness.get_device("mid_csp_cbf/sub_elt/controller")
        # mock_vcc = tango_harness.get_device("mid_csp_cbf/vcc/001")
        # mock_cbf_subarray_1 = tango_harness.get_device("mid_csp_cbf/sub_elt/subarray_01")
        # mock_fsp_pss_subarray_2_1 = tango_harness.get_device("mid_csp_cbf/fspPssSubarray/02_01")

        # mock_fsp_pss_subarray_2_1.Init()
        # mock_cbf_subarray_1.Init()
        # mock_vcc.Init()
        # for proxy in create_vcc_proxies:
        #     proxy.Init()


        # check initial values of attributes
        # TODO: why does device_under_test.receptors return None?
        # assert device_under_test.receptors == ()
        assert device_under_test.frequencyBand == 0
        assert (device_under_test.band5Tuning[0],
                device_under_test.band5Tuning[1]) == (0, 0)
        assert device_under_test.frequencySliceID == 0
        assert device_under_test.corrBandwidth == 0
        assert device_under_test.zoomWindowTuning == 0
        assert device_under_test.integrationTime == 0
        for i in range(20):
            assert device_under_test.channelAveragingMap[i][1] == 0

        # assert mock_fsp_pss_subarray_2_1.receptors == ()
        # assert mock_fsp_pss_subarray_2_1.searchBeams == ()
        # assert mock_fsp_pss_subarray_2_1.searchWindowID == 0
        # assert mock_fsp_pss_subarray_2_1.searchBeamID == ()
        # assert mock_fsp_pss_subarray_2_1.outputEnable == 0

        mock_cbf_subarray_1.AddReceptors([1, 10, 197])
        time.sleep(1)

        # configure search window
        f = open(file_path + "/../data/FspSubarray_ConfigureScan_basic.json")
        device_under_test.ConfigureScan(f.read().replace("\n", ""))
        f.close()

        assert mock_fsp_pss_subarray_2_1.receptors == (3, )
        assert mock_fsp_pss_subarray_2_1.searchWindowID == 2
        assert mock_fsp_pss_subarray_2_1.searchBeamID == (300, 400)

        assert device_under_test.receptors == (10, 197)
        assert device_under_test.frequencyBand == 4
        assert device_under_test.band5Tuning == (5.85, 7.25)
        assert device_under_test.frequencySliceID == 4
        assert device_under_test.corrBandwidth == 1
        assert device_under_test.zoomWindowTuning == 500000
        assert device_under_test.integrationTime == 140
        assert device_under_test.channelAveragingMap == (
            (1, 0),
            (745, 0),
            (1489, 0),
            (2233, 0),
            (2977, 0),
            (3721, 0),
            (4465, 0),
            (5209, 0),
            (5953, 0),
            (6697, 0),
            (7441, 0),
            (8185, 0),
            (8929, 0),
            (9673, 0),
            (10417, 0),
            (11161, 0),
            (11905, 0),
            (12649, 0),
            (13393, 0),
            (14137, 0)
        )