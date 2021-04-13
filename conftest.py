"""
A module defining a list of fixture functions that are shared across all the skabase
tests.
"""

from __future__ import absolute_import
#import mock
import pytest
import importlib
import sys
import time
sys.path.insert(0, "tangods/commons")

import tango
from tango import DevState
from tango import DeviceProxy
from tango.test_context import DeviceTestContext
import global_enum

from ska_tango_base.control_model import ObsState, AdminMode

@pytest.fixture(scope="class")
def cbf_master_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/master")

@pytest.fixture(scope="class")
def subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/subarray_01")

@pytest.fixture(scope="class")
def subarray_2_proxy():
    return DeviceProxy("mid_csp_cbf/sub_elt/subarray_02")

@pytest.fixture(scope="class")
def sw_1_proxy():
    return DeviceProxy("mid_csp_cbf/sw1/01")

@pytest.fixture(scope="class")
def sw_2_proxy():
    return DeviceProxy("mid_csp_cbf/sw2/01")

@pytest.fixture(scope="class")
def vcc_proxies():
    return [DeviceProxy("mid_csp_cbf/vcc/" + str(i + 1).zfill(3)) for i in range(4)]

@pytest.fixture(scope="class")
def vcc_band_proxies():
    return [[DeviceProxy("mid_csp_cbf/vcc_band{0}/{1:03d}".format(j, i + 1)) for j in ["12", "3", "4", "5"]] for i in range(4)]

@pytest.fixture(scope="class")
def vcc_tdc_proxies():
    return [[DeviceProxy("mid_csp_cbf/vcc_sw{0}/{1:03d}".format(j, i + 1)) for j in ["1", "2"]] for i in range(4)]

@pytest.fixture(scope="class")
def fsp_1_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/01")

@pytest.fixture(scope="class")
def fsp_2_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/02")

@pytest.fixture(scope="class")
def fsp_3_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/03")

@pytest.fixture(scope="class")
def fsp_4_proxy():
    return DeviceProxy("mid_csp_cbf/fsp/04")

@pytest.fixture(scope="class")
def fsp_1_function_mode_proxy():
    return [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/01".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

@pytest.fixture(scope="class")
def fsp_2_function_mode_proxy():
    return [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/02".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

@pytest.fixture(scope="class")
def fsp_1_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/01_01")

@pytest.fixture(scope="class")
def fsp_2_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspCorrSubarray/02_01")

@pytest.fixture(scope="class")
def fsp_3_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspPssSubarray/03_01")

@pytest.fixture(scope="class")
def fsp_4_subarray_1_proxy():
    return DeviceProxy("mid_csp_cbf/fspPssSubarray/04_01")

@pytest.fixture(scope="class")
def tm_telstate_proxy():
    return DeviceProxy("ska_mid/tm_leaf_node/csp_subarray_01")

@pytest.fixture(name="proxies", scope="session")
def init_proxies_fixture():

    class Proxies:
        def __init__(self):
            self.vcc = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/vcc/" + str(j + 1).zfill(3)) for j in range(4)]):
                proxy.Init()
                self.vcc[i + 1] = proxy

            self.vccBand = [[DeviceProxy("mid_csp_cbf/vcc_band{0}/{1:03d}".format(j, k + 1)) for j in ["12", "3", "4", "5"]] for k in range(4)]
            self.vccTdc = [[DeviceProxy("mid_csp_cbf/vcc_sw{0}/{1:03d}".format(j, i + 1)) for j in ["1", "2"]] for i in range(4)] 
            
            self.fspSubarray = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fspCorrSubarray/" + str(j + 1).zfill(2) + "_01") for j in range(2)]):
                proxy.Init()
                self.fspSubarray[i + 1] = proxy
            for i ,proxy in enumerate([DeviceProxy("mid_csp_cbf/fspPssSubarray/" + str(j + 3).zfill(2) + "_01") for j in range(2)]):
                proxy.Init()
                self.fspSubarray[i + 3] = proxy

            self.fsp1FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/01".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]
            self.fsp2FunctionMode = [*map(DeviceProxy, ["mid_csp_cbf/fsp_{}/02".format(i) for i in ["corr", "pss", "pst", "vlbi"]])]

            self.fsp = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/fsp/" + str(j + 1).zfill(2)) for j in range(4)]):
                proxy.Init()
                self.fsp[i + 1] = proxy

            self.sw = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/sw" + str(j + 1) + "/01") for j in range(2)]):
                proxy.Init()
                self.sw[i + 1] = proxy
            
            self.master = DeviceProxy("mid_csp_cbf/sub_elt/master")
            self.master.set_timeout_millis(60000)
            self.master.Init()
            timeout = time.time_ns() + 3_000_000_000
            while time.time_ns() < timeout:
                if self.master.State() == DevState.STANDBY: break
                time.sleep(0.1)
            
            self.receptor_to_vcc = dict([*map(int, pair.split(":"))] for pair in self.master.receptorToVcc)
            
            self.subarray = {}
            for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/sub_elt/subarray_" + str(i + 1).zfill(2)) for i in range(3)]):
                self.subarray[i + 1] = proxy
                self.subarray[i + 1].set_timeout_millis(60000)

            self.tm = DeviceProxy("ska_mid/tm_leaf_node/csp_subarray_01").Init()
    
    return Proxies()

@pytest.fixture(scope="class")
def clean_proxies():
    
    def clean_up(argin):
        # for i, proxy in enumerate([DeviceProxy("mid_csp_cbf/vcc/" + str(j + 1).zfill(3)) for j in range(4)]):
        #         proxy.Init()
        if "subarray" in argin:
            for proxy in [DeviceProxy("mid_csp_cbf/sub_elt/subarray_" + str(i + 1).zfill(2)) for i in range(argin["subarray"])]:
                if proxy.obsState == ObsState.READY:
                    proxy.GoToIdle()
                    timeout = time.time_ns() + 3_000_000_000
                    while time.time_ns() < timeout:
                        if proxy.obsState == ObsState.IDLE: break
                        time.sleep(0.01)
                if proxy.obsState == ObsState.IDLE:
                    proxy.RemoveAllReceptors()
                    timeout = time.time_ns() + 3_000_000_000
                    while time.time_ns() < timeout:
                        if proxy.obsState == ObsState.EMPTY: break
                        time.sleep(0.01)
                if proxy.obsState == ObsState.EMPTY:
                    proxy.Off()
                    timeout = time.time_ns() + 3_000_000_000
                    while time.time_ns() < timeout:
                        if proxy.State() == DevState.OFF: break
                        time.sleep(0.01)

    return clean_up

@pytest.fixture(scope="class")
def wait_timeout():
    def wait_timeout_method(proxygroup, state, time_ns, sleep_time_s):
        timeout = time.time_ns() + time_ns
        while time.time_ns() < timeout:
            for proxy in proxygroup:
                if proxy.State() == state: break
            time.sleep(sleep_time_s)
    return wait_timeout_method
