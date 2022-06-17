#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the Talon-DX component manager."""

import pytest
from ska_tango_base.commands import ResultCode

from ska_mid_cbf_mcs.controller.talondx_component_manager import \
    TalonDxComponentManager
from ska_mid_cbf_mcs.testing.tango_harness import TangoHarness


@pytest.mark.parametrize(
    "talon_dx_component_manager",
    [
        {
            "sim_connect_error": False,
            "sim_cmd_error": False,
            "sim_scp_error": False,
        }
    ],
    indirect=True,
)
def test_configure_talons_ssh_success(
    talon_dx_component_manager: TalonDxComponentManager,
    tango_harness: TangoHarness,
) -> None:
    """
    Tests the outcome of the configure_talons operation when the mocked
    SSH operations are successful.
    """
    result = talon_dx_component_manager.configure_talons()

    mock_ds_hps_master = tango_harness.get_device(
        "talondx-001/hpsmaster/hps-1"
    )
    if mock_ds_hps_master.stimulusMode == "success":
        assert result == ResultCode.OK
    else:
        assert result == ResultCode.FAILED


@pytest.mark.parametrize(
    "talon_dx_component_manager",
    [
        {
            "sim_connect_error": True,
            "sim_cmd_error": False,
            "sim_scp_error": False,
        }
    ],
    indirect=True,
)
def test_configure_talons_ssh_fail(
    talon_dx_component_manager: TalonDxComponentManager,
) -> None:
    """
    Tests the outcome of the configure_talons operation when the mocked
    SSH connection is not successful.
    """
    result = talon_dx_component_manager.configure_talons()
    assert result == ResultCode.FAILED


@pytest.mark.parametrize(
    "talon_dx_component_manager",
    [
        {
            "sim_connect_error": False,
            "sim_cmd_error": True,
            "sim_scp_error": False,
        }
    ],
    indirect=True,
)
def test_configure_talons_ssh_cmd_fail(
    talon_dx_component_manager: TalonDxComponentManager,
) -> None:
    """
    Tests the outcome of the configure_talons operation when the mocked
    remote command fails.
    """
    result = talon_dx_component_manager.configure_talons()
    assert result == ResultCode.FAILED


@pytest.mark.parametrize(
    "talon_dx_component_manager",
    [
        {
            "sim_connect_error": False,
            "sim_cmd_error": False,
            "sim_scp_error": True,
        }
    ],
    indirect=True,
)
def test_configure_talons_sco_fail(
    talon_dx_component_manager: TalonDxComponentManager,
) -> None:
    """
    Tests the outcome of the configure_talons operation when the SCP fails.
    """
    result = talon_dx_component_manager.configure_talons()
    assert result == ResultCode.FAILED
