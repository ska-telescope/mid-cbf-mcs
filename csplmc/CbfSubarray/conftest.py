"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import importlib
import sys
sys.path.insert(0, "../commons")

from tango import DeviceProxy
from tango.test_context import DeviceTestContext
import global_enum

@pytest.fixture(scope="class")
def create_cbf_master_proxy():
    return DeviceProxy("mid_csp_cbf/master/main")

@pytest.fixture(scope="class")
def create_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/cbfSubarray/01")

@pytest.fixture(scope="class")
def create_subarray_2_proxy():
    return DeviceProxy("mid_csp_cbf/cbfSubarray/02")

@pytest.fixture(scope="class")
def create_vcc_proxies():
    return [DeviceProxy("mid_csp_cbf/vcc/" + str(i + 1).zfill(3)) for i in range(197)]

@pytest.fixture(scope="class")
def create_vcc_band_proxies():
    return [[DeviceProxy("mid_csp_cbf/vcc_band{0}/{1:03d}".format(j, i + 1)) for j in ["12", "3", "4", "5"]] for i in range(197)]

@pytest.fixture(scope="class")
def create_vcc_tdc_proxies():
    return [[DeviceProxy("mid_csp_cbf/vcc_tdc{0}/{1:03d}".format(j, i + 1)) for j in ["1", "2"]] for i in range(197)]

@pytest.fixture(scope="class")
def create_fsp_1_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/01")

@pytest.fixture(scope="class")
def create_fsp_2_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/02")

@pytest.fixture(scope="class")
def create_fsp_1_function_mode_proxy():
    return [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/01".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

@pytest.fixture(scope="class")
def create_fsp_2_function_mode_proxy():
    return [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/02".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

@pytest.fixture(scope="class")
def create_fsp_1_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspSubarray/01_01")

@pytest.fixture(scope="class")
def create_fsp_2_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspSubarray/02_01")

@pytest.fixture(scope="class")
def create_tm_telstate_proxy():
    return DeviceProxy("ska1_mid/tm/telmodel")
