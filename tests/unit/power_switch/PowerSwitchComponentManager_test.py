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
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import PowerState

from ska_mid_cbf_mcs.power_switch.power_switch_component_manager import (
    PowerSwitchComponentManager,
)


@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{"sim_patch_error": False, "sim_get_error": False}],
    indirect=True,
)
def test_get_outlet_state(
    power_switch_component_manager: PowerSwitchComponentManager,
) -> None:
    """
    Tests that we can get the state of every outlet.
    """
    power_switch_component_manager.start_communicating()
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    for i in range(0, num_outlets):
        assert (
            power_switch_component_manager.get_outlet_power_mode(str(i))
            == PowerState.ON
        )


@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{"sim_patch_error": False, "sim_get_error": False}],
    indirect=True,
)
def test_turn_outlet_on_off(
    power_switch_component_manager: PowerSwitchComponentManager,
) -> None:
    """
    Tests that the outlets can be turned on and off individually.
    """
    power_switch_component_manager.start_communicating()
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    # Check initial state
    for i in range(0, num_outlets):
        assert (
            power_switch_component_manager.get_outlet_power_mode(str(i))
            == PowerState.ON
        )

    # Turn outlets off and check the state again
    for i in range(0, num_outlets):
        assert power_switch_component_manager.turn_off_outlet(str(i)) == (
            ResultCode.OK,
            f"Outlet {i} power off",
        )

        for j in range(0, num_outlets):
            if j <= i:
                with pytest.raises(
                    AssertionError,
                    match=r"Power mode of outlet ID \w \(3\) is different than the expected mode 1",
                ):
                    power_switch_component_manager.get_outlet_power_mode(
                        str(j)
                    )
            else:
                assert (
                    power_switch_component_manager.get_outlet_power_mode(
                        str(j)
                    )
                    == PowerState.ON
                )

    # Turn on outlets and check the state again
    for i in range(0, num_outlets):
        assert power_switch_component_manager.turn_on_outlet(str(i)) == (
            ResultCode.OK,
            f"Outlet {i} power on",
        )

        for j in range(0, num_outlets):
            if j <= i:
                assert (
                    power_switch_component_manager.get_outlet_power_mode(
                        str(j)
                    )
                    == PowerState.ON
                )
            else:
                with pytest.raises(
                    AssertionError,
                    match=r"Power mode of outlet ID \w \(3\) is different than the expected mode 1",
                ):
                    power_switch_component_manager.get_outlet_power_mode(
                        str(j)
                    )


@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{"sim_patch_error": False, "sim_get_error": False}],
    indirect=True,
)
def test_outlet_out_of_bounds(
    power_switch_component_manager: PowerSwitchComponentManager,
) -> None:
    """
    Tests that the power switch driver does not query the power switch with
    an outlet number that is invalid.
    """
    power_switch_component_manager.start_communicating()
    # Check that the number of outlets is 8, since that is what our mock response returns
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    # Check that an assertion is raised if we try to access an invalid outlet ID
    with pytest.raises(AssertionError):
        power_switch_component_manager.get_outlet_power_mode(str(num_outlets))

    with pytest.raises(AssertionError):
        power_switch_component_manager.turn_on_outlet(str(num_outlets))

    with pytest.raises(AssertionError):
        power_switch_component_manager.turn_off_outlet(str(num_outlets))


@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{"sim_patch_error": False, "sim_get_error": True}],
    indirect=True,
)
def test_get_request_failure(
    power_switch_component_manager: PowerSwitchComponentManager,
) -> None:
    """
    Tests that a GET request failure is appropriately handled.
    """
    power_switch_component_manager.start_communicating()
    assert power_switch_component_manager.is_communicating is False
    assert power_switch_component_manager.num_outlets == 0


@pytest.mark.parametrize(
    "power_switch_component_manager",
    [{"sim_patch_error": True, "sim_get_error": False}],
    indirect=True,
)
def test_patch_request_failure(
    power_switch_component_manager: PowerSwitchComponentManager,
) -> None:
    """
    Tests that a PATCH request failure is appropriately handled.
    """
    power_switch_component_manager.start_communicating()
    num_outlets = power_switch_component_manager.num_outlets
    assert num_outlets == 8

    assert power_switch_component_manager.turn_off_outlet("0") == (
        ResultCode.FAILED,
        "HTTP response error",
    )
