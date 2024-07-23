from __future__ import annotations

import os
from logging import getLogger

import pytest
from src.ska_mid_cbf_mcs.subarray.subarray_component_manager import CbfSubarrayComponentManager, ScanConfigurationValidator

# Path
file_path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"

class TestScanConfigurationValidator:
    logger = getLogger()
    @pytest.mark.parametrize(
        "config_file_name", [("ConfigureScan_1_0_CORR.json"),
                             ("ConfigureScan_19_0_CORR.json")]
    )
    def test_Invalid_Configuration_Version(
            self:TestScanConfigurationValidator,
            subarray_component_manager: CbfSubarrayComponentManager,
            config_file_name: str):
        path_to_test_json = os.path.join(file_path,config_file_name)
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator:ScanConfigurationValidator = ScanConfigurationValidator(json_str, subarray_component_manager,self.logger)
        result_code, msg = validator.validate_input()
        print(msg)
        assert("The version defined in the Scan Configuration is not supported by MCS:" in msg)
        assert(result_code == False)
    
    
    @pytest.mark.parametrize(
        "config_file_name,\
         receptors", 
        [("ConfigureScan_4_0_CORR.json",
          ["SKA001", "SKA036", "SKA063", "SKA100"],),
         ("ConfigureScan_basic_CORR.json",
          ["SKA001", "SKA036", "SKA063", "SKA100"],)]
    )  
    def test_Valid_Configuration_Version(
            self:TestScanConfigurationValidator,
            subarray_component_manager: CbfSubarrayComponentManager,
            config_file_name: str,
            receptors: list[str]):
        path_to_test_json = os.path.join(file_path,config_file_name)
        
        subarray_component_manager.start_communicating()

        with open(file_path + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        subarray_component_manager.assign_vcc(receptors)
        
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator:ScanConfigurationValidator = ScanConfigurationValidator(json_str, subarray_component_manager,self.logger)
        result_code, msg = validator.validate_input()
        print(msg)
        assert("Scan configuration is valid." in msg)
        assert(result_code == True)