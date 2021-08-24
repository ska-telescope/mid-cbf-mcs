#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the csp-lmc-prototype project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the CbfController."""

# Standard imports
import sys
import os
import time
import json

# Path
file_path = os.path.dirname(os.path.abspath(__file__))

# Tango imports
import tango
from tango import DevState
import pytest

#Local imports

from ska_tango_base.control_model import HealthState, AdminMode, ObsState

# @pytest.mark.usefixtures(
#     "create_cbf_controller_proxy",
#     "create_vcc_proxies",
#     "create_fsp_proxy",
#     "create_cbf_subarray_1_proxy",
#     "create_fsp_corr_subarray_1_1_proxy"
# )

@pytest.mark.skip(reason="this class is currently untested")
class TestFspCorrSubarray:
    """
    @classmethod
    def mocking(cls):
    """#Mock external libraries.
    """
        # Example : Mock numpy
        # cls.numpy = CspController.numpy = MagicMock()
    """

    def test_AddRemoveReceptors_valid(
            self,
            create_cbf_controller_proxy,
            create_vcc_proxies,
            create_cbf_subarray_1_proxy,
            create_fsp_corr_subarray_1_1_proxy,
            create_fsp_pss_subarray_2_1_proxy
    ):
        """
        Test valid AddReceptors and RemoveReceptors commands
        """
        create_fsp_corr_subarray_1_1_proxy.Init()
        create_fsp_pss_subarray_2_1_proxy.Init()
        create_cbf_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_cbf_subarray_1_proxy.receptors == ()
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()
        assert create_fsp_pss_subarray_2_1_proxy.receptors == ()

        # add some receptors
        create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_cbf_subarray_1_proxy.receptors == (1, 10, 197)
        create_fsp_corr_subarray_1_1_proxy.AddReceptors([1, 10])
        create_fsp_pss_subarray_2_1_proxy.AddReceptors([2, 9])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
        assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10
        assert create_fsp_pss_subarray_2_1_proxy.receptors[0] == 2
        assert create_fsp_pss_subarray_2_1_proxy.receptors[1] == 9

        # add more receptors
        create_fsp_corr_subarray_1_1_proxy.AddReceptors([197])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[2] == 197

        # remove some receptors
        create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([10, 197])
        create_fsp_pss_subarray_2_1_proxy.RemoveReceptors([2, 9])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1

        # remove remaining receptors
        create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([1])
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()
        assert create_fsp_pss_subarray_2_1_proxy.receptors == ()

    def test_AddRemoveReceptors_invalid(
            self,
            create_vcc_proxies,
            create_cbf_controller_proxy,
            create_cbf_subarray_1_proxy,
            create_fsp_corr_subarray_1_1_proxy,
            create_fsp_pss_subarray_2_1_proxy
    ):
        """
        Test invalid AddReceptors and RemoveReceptors commands:
            - when a receptor to be added is not in use by the subarray
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        """
        create_fsp_corr_subarray_1_1_proxy.Init()
        create_fsp_pss_subarray_2_1_proxy.Init()
        create_cbf_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()
        receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in
                               create_cbf_controller_proxy.receptorToVcc)

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_cbf_subarray_1_proxy.receptors == ()
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()
        assert create_fsp_pss_subarray_2_1_proxy.receptors == ()

        # add some receptors
        create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_cbf_subarray_1_proxy.receptors == (1, 10, 197)
        create_fsp_corr_subarray_1_1_proxy.AddReceptors([1, 10])
        create_fsp_pss_subarray_2_1_proxy.AddReceptors([2, 9])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
        assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10
        assert create_fsp_pss_subarray_2_1_proxy.receptors[0] == 2
        assert create_fsp_pss_subarray_2_1_proxy.receptors[1] == 9

        # try adding a receptor not in use by the subarray
        assert create_vcc_proxies[receptor_to_vcc[17] - 1].subarrayMembership == 0
        with pytest.raises(tango.DevFailed) as df:
            create_fsp_corr_subarray_1_1_proxy.AddReceptors([17])
        assert "does not belong" in str(df.value.args[0].desc)
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
        assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

        # try adding an invalid receptor ID
        with pytest.raises(tango.DevFailed) as df:
            create_fsp_corr_subarray_1_1_proxy.AddReceptors([200])
        time.sleep(1)
        assert "Invalid receptor ID" in str(df.value.args[0].desc)

        # try removing a receptor not assigned to subarray 2
        # doing this doesn't actually throw an error
        create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([5])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
        assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

        # remove all receptors
        create_fsp_corr_subarray_1_1_proxy.RemoveReceptors([1, 10])
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

    def test_RemoveAllReceptors(
            self,
            create_vcc_proxies,
            create_cbf_subarray_1_proxy,
            create_fsp_corr_subarray_1_1_proxy
    ):
        """
        Test RemoveAllReceptors command
        """
        create_fsp_corr_subarray_1_1_proxy.Init()
        create_cbf_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # receptor list should be empty right after initialization
        assert create_cbf_subarray_1_proxy.receptors == ()
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

        # add some receptors
        create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)
        assert create_cbf_subarray_1_proxy.receptors == (1, 10, 197)
        create_fsp_corr_subarray_1_1_proxy.AddReceptors([1, 10])
        assert create_fsp_corr_subarray_1_1_proxy.receptors[0] == 1
        assert create_fsp_corr_subarray_1_1_proxy.receptors[1] == 10

        # remove all receptors
        create_fsp_corr_subarray_1_1_proxy.RemoveAllReceptors()
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()

    def test_ConfigureScan_basic(
            self,
            create_vcc_proxies,
            create_cbf_subarray_1_proxy,
            create_fsp_corr_subarray_1_1_proxy,
            create_fsp_pss_subarray_2_1_proxy
    ):
        """
        Test a minimal successful scan configuration.
        """
        create_fsp_corr_subarray_1_1_proxy.Init()
        create_fsp_pss_subarray_2_1_proxy.Init()
        create_cbf_subarray_1_proxy.Init()
        for proxy in create_vcc_proxies:
            proxy.Init()

        time.sleep(3)

        # check initial values of attributes
        assert create_fsp_corr_subarray_1_1_proxy.receptors == ()
        assert create_fsp_corr_subarray_1_1_proxy.frequencyBand == 0
        assert create_fsp_corr_subarray_1_1_proxy.band5Tuning == None
        assert create_fsp_corr_subarray_1_1_proxy.frequencySliceID == 0
        assert create_fsp_corr_subarray_1_1_proxy.corrBandwidth == 0
        assert create_fsp_corr_subarray_1_1_proxy.zoomWindowTuning == 0
        assert create_fsp_corr_subarray_1_1_proxy.integrationTime == 0
        assert create_fsp_corr_subarray_1_1_proxy.channelAveragingMap == \
            tuple([(0, 0) for i in range(20)])

        assert create_fsp_pss_subarray_2_1_proxy.receptors == ()
        assert create_fsp_pss_subarray_2_1_proxy.searchBeams == ()
        assert create_fsp_pss_subarray_2_1_proxy.searchWindowID == 0
        assert create_fsp_pss_subarray_2_1_proxy.searchBeamID == ()
        assert create_fsp_pss_subarray_2_1_proxy.outputEnable == 0

        create_cbf_subarray_1_proxy.AddReceptors([1, 10, 197])
        time.sleep(1)

        # configure search window
        f = open(file_path + "/../data/FspSubarray_ConfigureScan_basic.json")
        create_fsp_corr_subarray_1_1_proxy.ConfigureScan(f.read().replace("\n", ""))
        f.close()

        assert create_fsp_pss_subarray_2_1_proxy.receptors == (3, )
        assert create_fsp_pss_subarray_2_1_proxy.searchWindowID == 2
        assert create_fsp_pss_subarray_2_1_proxy.searchBeamID == (300, 400)

        assert create_fsp_corr_subarray_1_1_proxy.receptors == (10, 197)
        assert create_fsp_corr_subarray_1_1_proxy.frequencyBand == 4
        assert create_fsp_corr_subarray_1_1_proxy.band5Tuning == (5.85, 7.25)
        assert create_fsp_corr_subarray_1_1_proxy.frequencySliceID == 4
        assert create_fsp_corr_subarray_1_1_proxy.corrBandwidth == 1
        assert create_fsp_corr_subarray_1_1_proxy.zoomWindowTuning == 500000
        assert create_fsp_corr_subarray_1_1_proxy.integrationTime == 140
        assert create_fsp_corr_subarray_1_1_proxy.channelAveragingMap == (
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
