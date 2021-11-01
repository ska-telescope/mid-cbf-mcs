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
import scp
import paramiko
from typing import Any, Dict

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
                            "sim_connect_error": boolean,
                            "sim_cmd_error": boolean,
                            "sim_scp_error": boolean
                        }
    :param monkeypatch: the pytest monkey-patching fixture

    :return: a Talon-DX component manager.
    """

    def mock_connect(
        *args: Any, **kwargs: Any
    ) -> None:
        """
        Replace paramiko.SSHClient.connect method with a mock method.

        :param args: arguments to the mocked function
        :param kwargs: keyword arguments to the mocked function

        :raise: socket.gaierror if sim_error is True
        """
        assert args[1] == "169.254.100.1"
        assert kwargs["username"] == "root"
        assert kwargs["password"] == ""

        if request.param["sim_connect_error"]:
            raise paramiko.ssh_exception.NoValidConnectionsError({('169.254.100.1', 22): "Exception"})

    def mock_exec_command(
        *args: Any, **kwargs: Any
    ) -> None:
        """
        Replace paramiko.SSHClient.exec_command method with a mock method.

        :param args: arguments to the mocked function
        :param kwargs: keyword arguments to the mocked function

        :raise: paramiko.SSHException if sim_error is True
        """
        assert (
            (args[1] == "mkdir -p /lib/firmware/hps_software/vcc_test") or
            (args[1] == "mkdir -p /lib/firmware") or
            (args[1] == "/lib/firmware/hps_software/hps_master_mcs.sh talon1_test")
        )

        if request.param["sim_connect_error"]:
            raise paramiko.ssh_exception.SSHException()

    def mock_recv_exit_status(
        *args: Any, **kwargs: Any
    ) -> None:
        """
        Replace paramiko.Channel.recv_exit_status() method with a mock method.

        :param args: arguments to the mocked function
        :param kwargs: keyword arguments to the mocked function

        :returns: Mocked exit status
        """
        if request.param["sim_cmd_error"]:
            return 255
        else:
            return 0

    class MockTransport:
        """
        Class to mock the paramiko.Transport object. Does not do anything useful.
        """
        def __init__(self: MockTransport) -> None:
            pass

        def getpeername(self: MockTransport) -> str:
            return "fake_name"

        def open_session(self: MockTransport) -> paramiko.Channel:
            return paramiko.Channel(0)

    def mock_get_transport(
        *args: Any, **kwargs: Any
    ) -> MockTransport:
        """
        Replace paramiko.SSHClient.get_transport() method with a mock method.

        :param args: arguments to the mocked function
        :param kwargs: keyword arguments to the mocked function

        :return: mocked Transport object
        """
        return MockTransport()

    def mock_scp_put(
        *args: Any, **kwargs: Any
    ) -> None:
        """
        Replace scp.SCPClient.put method with a mock method.

        :param args: arguments to the mocked function
        :param kwargs: keyword arguments to the mocked function

        :raise: scp.SCPException if sim_error is True
        """
        src_ds = re.compile(r"tests\/unit\/talondx_component_manager\/.+\/bin\/.*")
        src_fpga = re.compile(r"tests\/unit\/talondx_component_manager\/fpga-.*\/bin\/vcc3_2ch4.*")
        assert (src_ds.fullmatch(args[1]) or src_fpga.fullmatch(args[1]))

        target_dest_ds = re.compile(r"\/lib\/firmware\/hps_software(\/vcc_test)?")
        target_dest_fpga = re.compile(r"\/lib\/firmware")
        assert (target_dest_ds.fullmatch(kwargs["remote_path"]) or target_dest_fpga.fullmatch(kwargs["remote_path"]))

        if request.param["sim_scp_error"]:
            raise scp.SCPException()
   
    monkeypatch.setattr(paramiko.SSHClient, "connect", mock_connect)
    monkeypatch.setattr(paramiko.Channel, "exec_command", mock_exec_command)
    monkeypatch.setattr(paramiko.Channel, "recv_exit_status", mock_recv_exit_status)
    monkeypatch.setattr(paramiko.SSHClient, "get_transport", mock_get_transport)
    monkeypatch.setattr(scp.SCPClient, "put", mock_scp_put)

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
