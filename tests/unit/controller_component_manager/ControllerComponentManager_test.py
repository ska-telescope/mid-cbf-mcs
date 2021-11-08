#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the mid-cbf-mcs project
#
#
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

"""Contain the tests for the CbfController component manager."""
from ska_mid_cbf_mcs.controller.controller_component_manager import ControllerComponentManager
from ska_tango_base.commands import ResultCode

def test_On(
    controller_component_manager: ControllerComponentManager,
) -> None:
    """
    Test on().
    """
    assert controller_component_manager._connected == True
    (result_code, _) = controller_component_manager.on()
    assert result_code == ResultCode.OK

def test_Off(
    controller_component_manager: ControllerComponentManager,
) -> None:
    """
    Test off().
    """
    assert controller_component_manager._connected == True
    (result_code, _) = controller_component_manager.off()
    assert result_code == ResultCode.OK

def test_Standby(
    controller_component_manager: ControllerComponentManager,
) -> None:
    """
    Test standby().
    """
    assert controller_component_manager._connected == True
    (result_code, _) = controller_component_manager.standby()
    assert result_code == ResultCode.OK