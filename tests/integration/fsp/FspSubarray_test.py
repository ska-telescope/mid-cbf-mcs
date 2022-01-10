#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE for more info.
"""Contain the tests for the FspSubarray."""

from __future__ import annotations
from re import sub

# Standard imports
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, cast
import time
import random
import json


# Tango imports
import tango
from tango import DevState, DeviceProxy
import pytest

# SKA imports

from ska_tango_base.control_model import HealthState, AdminMode, ObsState


class TestFspPstSubarray:
    """
    Test class for FspPstSubarray device class integration testing.
    """

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_On(
        self: TestFspPstSubarray,
        test_proxies: pytest.fixture,
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test for FspPstSubarray device On command.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the FspPstSubarray under test.
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        device_under_test.On()
        test_proxies.wait_timeout_dev([device_under_test], DevState.ON, 3, 1)
        assert device_under_test.State() == DevState.ON

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_Off(
        self: TestFspPstSubarray,
        test_proxies: pytest.fixture,
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test for FspPstSubarray device Off command.

        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the FspPstSubarray under test.
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        device_under_test.Off()
        test_proxies.wait_timeout_dev([device_under_test], DevState.OFF, 3, 1)
        assert device_under_test.State() == DevState.OFF

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_AddRemoveReceptors_valid(
        self: TestFspPstSubarray,
        test_proxies: pytest.fixture,
        receptors_to_test: List[int],
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test valid AddReceptors and RemoveReceptors commands
        
        :param subarray: fixture that provides a
            :py:class:`tango.DeviceProxy` to the CbfSubarray under test.
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the FspPstSubarray under test.
        :param receptors_to_test: fixture that provides a random list of 
            receptor IDs
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        subarray = test_proxies.subarray[sub_id]

        # TODO implement proper reset of proxies for this test class
        if subarray.State() == DevState.OFF:
            subarray.On()
            test_proxies.wait_timeout_dev([device_under_test], DevState.ON, 3, 1)
        if subarray.ObsState == ObsState.FAULT:
            subarray.Restart()
            test_proxies.wait_timeout_dev([device_under_test], ObsState.EMPTY, 3, 1)
        elif len(subarray.receptors) != 0:
            subarray.RemoveAllReceptors()
            time.sleep(1)
        if len(device_under_test.receptors) != 0:
            device_under_test.RemoveAllReceptors()
            time.sleep(1)

        # receptor list should be empty right after initialization
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []
        device_under_test.On()

        # add some receptors
        subarray.AddReceptors(receptors_to_test)
        time.sleep(1)
        assert [subarray.receptors[i] for i in range(len(subarray.receptors))] \
            == receptors_to_test
        device_under_test.AddReceptors(receptors_to_test[:-1])
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test[:-1]

        # add more receptors
        device_under_test.AddReceptors([receptors_to_test[-1]])
        assert device_under_test.receptors[-1] == receptors_to_test[-1]

        # remove some receptors
        random_receptor = random.choice(receptors_to_test)
        receptors_to_test.remove(random_receptor)
        device_under_test.RemoveReceptors([random_receptor])
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # remove remaining receptors
        subarray.RemoveAllReceptors()
        time.sleep(1)
        device_under_test.RemoveReceptors(receptors_to_test)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_AddRemoveReceptors_invalid(
        self: TestFspPstSubarray,
        test_proxies: pytest.fixture,
        receptors_to_test: List[int],
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test invalid AddReceptors and RemoveReceptors commands:
            - when a receptor to be added is not in use by the subarray
            - when a receptor ID is invalid (e.g. out of range)
            - when a receptor to be removed is not assigned to the subarray
        
        :param subarray: fixture that provides a
            :py:class:`tango.DeviceProxy` to the CbfSubarray under test.
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the FspPstSubarray under test.
        :param receptors_to_test: fixture that provides a random list of 
            receptor IDs
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        subarray = test_proxies.subarray[sub_id]

        # receptor list should be empty right after initialization
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []

        # add some receptors
        subarray.AddReceptors(receptors_to_test)
        time.sleep(1)
        assert [subarray.receptors[i] for i in range(len(subarray.receptors))] \
            == receptors_to_test
        device_under_test.AddReceptors(receptors_to_test)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # try adding a receptor not in use by the subarray
        with pytest.raises(tango.DevFailed) as df:
            device_under_test.AddReceptors([4])
        assert "does not belong" in str(df.value.args[0].desc)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # try adding an invalid receptor ID
        with pytest.raises(tango.DevFailed) as df:
            device_under_test.AddReceptors([200])
        time.sleep(1)
        assert "Invalid receptor ID" in str(df.value.args[0].desc)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # try removing a receptor not assigned to subarray 2
        # doing this doesn't actually throw an error
        device_under_test.RemoveReceptors([197])
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # remove all receptors
        subarray.RemoveAllReceptors()
        time.sleep(1)
        device_under_test.RemoveReceptors(receptors_to_test)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []

    @pytest.mark.parametrize(
        "fsp_id, \
        sub_id", 
        [(1, 1)]
    )
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
    def test_RemoveAllReceptors(
        self: TestFspPstSubarray,
        test_proxies: pytest.fixture,
        receptors_to_test: List[int],
        fsp_id: int,
        sub_id: int
    ) -> None:
        """
        Test RemoveAllReceptors command
        
        :param subarray: fixture that provides a
            :py:class:`tango.DeviceProxy` to the CbfSubarray under test.
        :param device_under_test: fixture that provides a
            :py:class:`tango.DeviceProxy` to the FspPstSubarray under test.
        :param receptors_to_test: fixture that provides a random list of 
            receptor IDs
        """
        device_under_test = test_proxies.fspSubarray["PST-BF"][sub_id][fsp_id]
        subarray = test_proxies.subarray[sub_id]

        # receptor list should be empty right after initialization
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []

        # add some receptors
        subarray.AddReceptors(receptors_to_test)
        time.sleep(1)
        assert [subarray.receptors[i] for i in range(len(subarray.receptors))] \
            == receptors_to_test
        device_under_test.AddReceptors(receptors_to_test)
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == receptors_to_test

        # remove all receptors
        subarray.RemoveAllReceptors()
        time.sleep(1)
        device_under_test.RemoveAllReceptors()
        assert [device_under_test.receptors[i] \
            for i in range(len(device_under_test.receptors))] == []

# TODO: fix and move to its own test file
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
    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
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

    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
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

    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
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

    @pytest.mark.skip(
        reason="Not updated to version 0.11.3 of the base classes."
    )
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
