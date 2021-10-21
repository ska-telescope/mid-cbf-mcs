# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""This module contains pytest-specific test harness for TalonDxComponentManager unit tests."""

from __future__ import annotations

# Standard imports
import re
import logging
import pytest
import unittest
import subprocess
from typing import Any, Dict, List

# Local imports
from ska_mid_cbf_mcs.controller.talondx_component_manager import TalonDxComponentManager
from ska_tango_base.control_model import SimulationMode
from ska_mid_cbf_mcs.testing.mock.mock_device import MockDeviceBuilder

@pytest.fixture(scope="function")
def talon_dx_component_manager(
    logger: logging.Logger,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> TalonDxComponentManager:
    """
    Return a Talon-DX component manager (with SSH connection monkey-patched).

    :param logger: the logger fixture
    :param request: the pytest request fixture, must be indirectly parametrized 
                    by each test with a dict of the form:
                        { 
                            "sim_error": boolean
                        }
    :param monkeypatch: the pytest monkey-patching fixture

    :return: a Talon-DX component manager.
    """

    class MockCompletedProcess:
        """A mock class to replace subprocess.CompletedProcess."""

        def __init__(
            self: MockCompletedProcess,
            cmd: List(str),
            simulate_response_error: bool
        ) -> None:
            """
            Initialise a new instance.

            :param cmd: Command that was sent
            :param simulate_response_error: set to True to simulate error response

            :raise: subprocess.CalledProcessError if simulate_response_error is True
            """
            self.args = cmd

            # Check that the arguments to the command are correct
            if cmd[0] == "scp":
                src_ds = re.compile(r"tests\/unit\/talondx_component_manager\/.+\/build-ci-cross\/bin\/.*")
                src_fpga = re.compile(r"tests\/unit\/talondx_component_manager\/fpga-.*\/bin\/vcc3_2ch4.*")
                assert (src_ds.fullmatch(cmd[1]) or src_fpga.fullmatch(cmd[1]))

                target_dest_ds = re.compile(r"root@talon1:\/lib\/firmware\/hps_software(\/vcc_test)?")
                target_dest_fpga = re.compile(r"root@talon1:\/lib\/firmware\/bitstream")
                assert (target_dest_ds.fullmatch(cmd[2]) or target_dest_fpga.fullmatch(cmd[2]))
            else:
                assert cmd[0] == "ssh"
                assert cmd[1] == "root@talon1"
                assert (
                    (cmd[2] == "mkdir -p /lib/firmware/hps_software/vcc_test") or
                    (cmd[2] == "mkdir -p /lib/firmware/bitstream") or
                    (cmd[2] == "source /lib/firmware/hps_software/run_hps_master.sh talon1_test")
                )

            if simulate_response_error:
                self.returncode = 255
                raise subprocess.CalledProcessError(cmd=cmd, returncode=255)
            else:
                self.returncode = 0

    def mock_subprocess_run(
        cmd: List(str), **kwargs: Any
    ) -> MockCompletedProcess:
        """
        Replace subprocess.run method with a mock method.

        :param cmd: the command that was sent
        :param kwargs: other keyword args

        :return: a mocked CompletedResponse
        :raise: subprocess.CalledProcessError if sim_error is True
        """
        return MockCompletedProcess(cmd, request.param["sim_error"])

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    return TalonDxComponentManager(
        "tests/unit/talondx_component_manager",
        SimulationMode.FALSE,
        logger
    )

@pytest.fixture(params=[
    "success",
    "fail"
])
def mock_ds_hps_master(request: pytest.FixtureRequest) -> unittest.mock.Mock:
    """
    Get a mock DsHpsMaster device. This fixture is parameterized to
    mock different pass / failure scenarios.

    :param request: the pytest request fixture which holds information about the
                    parameterization of this fixture
    :return: a mock DsHpsMaster device
    """
    builder = MockDeviceBuilder()
    builder.add_attribute("stimulusMode", request.param) # Attribute only used by tests

    if request.param == "success":
        builder.add_command("configure", 0)
    else:
        builder.add_command("configure", 1)

    return builder()

@pytest.fixture()
def initial_mocks(
    mock_ds_hps_master: unittest.mock.Mock,
) -> Dict[str, unittest.mock.Mock]:
    """
    Return a dictionary of device proxy mocks to pre-register.

    :param mock_ds_hps_master: a mock DsHpsMaster device
    :return: a dictionary of device proxy mocks to pre-register.
    """
    return {
        "talondx-001/hpsmaster/hps-1": mock_ds_hps_master,
    }
