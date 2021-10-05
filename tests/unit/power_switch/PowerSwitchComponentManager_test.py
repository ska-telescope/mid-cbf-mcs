#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.
"""Contain the tests for the power switch component manager."""

# Standard imports
import pytest
from ska_mid_cbf_mcs.commons.global_enum import PowerMode

# Local imports
from ska_tango_base.commands import ResultCode

@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{
        "sim_put_error": False,
        "sim_get_error": False
    }],
    indirect=True)
def test_get_outlet_state(power_switch_component_manager):
    """
    Tests that we can get the state of every outlet.
    """
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    for i in range(0, num_outlets):
        assert power_switch_component_manager.get_outlet_power_mode(i) == PowerMode.ON

@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{
        "sim_put_error": False,
        "sim_get_error": False
    }],
    indirect=True)
def test_turn_outlet_on_off(power_switch_component_manager):
    """
    Tests that the outlets can be turned on and off individually.
    """
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    # Check initial state
    for i in range(0, num_outlets):
        assert power_switch_component_manager.get_outlet_power_mode(i) == PowerMode.ON

    # Turn outlets off and check the state again
    for i in range(0, num_outlets):
        assert power_switch_component_manager.turn_off_outlet(i) == (
            ResultCode.OK, f"Outlet {i} power off")

        for j in range(0, num_outlets):
            if j <= i:
                assert power_switch_component_manager.get_outlet_power_mode(j) == PowerMode.OFF
            else:
                assert power_switch_component_manager.get_outlet_power_mode(j) == PowerMode.ON

    # Turn on outlets and check the state again
    for i in range(0, num_outlets):
        assert power_switch_component_manager.turn_on_outlet(i) == (
            ResultCode.OK, f"Outlet {i} power on")

        for j in range(0, num_outlets):
            if j <= i:
                assert power_switch_component_manager.get_outlet_power_mode(j) == PowerMode.ON
            else:
                assert power_switch_component_manager.get_outlet_power_mode(j) == PowerMode.OFF

@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{
        "sim_put_error": False,
        "sim_get_error": False
    }],
    indirect=True)
def test_outlet_out_of_bounds(power_switch_component_manager):
    """
    Tests that the power switch driver does not query the power switch with
    an outlet number that is invalid.
    """
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    # Check that an assertion is raised if we try to access an invalid outlet ID
    with pytest.raises(AssertionError):
        power_switch_component_manager.get_outlet_power_mode(num_outlets)
    
    with pytest.raises(AssertionError):
        power_switch_component_manager.turn_on_outlet(num_outlets)

    with pytest.raises(AssertionError):
        power_switch_component_manager.turn_off_outlet(num_outlets)

@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{
        "sim_put_error": False,
        "sim_get_error": True
    }],
    indirect=True)
def test_get_request_failure(power_switch_component_manager):
    """
    Tests that a GET request failure is appropriately handled.
    """
    assert power_switch_component_manager.is_communicating == False
    assert power_switch_component_manager.num_outlets == 0

@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{
        "sim_put_error": True,
        "sim_get_error": False
    }],
    indirect=True)
def test_put_request_failure(power_switch_component_manager):
    """
    Tests that a PUT request failure is appropriately handled.
    """
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    assert power_switch_component_manager.turn_off_outlet(0) == (
        ResultCode.FAILED, "HTTP response error")