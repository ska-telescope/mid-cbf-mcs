from __future__ import annotations

import os
from logging import getLogger

import pytest
from src.ska_mid_cbf_mcs.commons.scan_configuration_validator import ScanConfigurationValidator

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
            config_file_name: str):
        path_to_test_json = os.path.join(file_path,config_file_name)
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator:ScanConfigurationValidator = ScanConfigurationValidator(json_str, self.logger)
        result_code, msg = validator.validate_input()
        print(msg)
        assert("The version defined in the Scan Configuration is not supported by MCS:" in msg)
        assert(result_code == False)
    
    
    @pytest.mark.parametrize(
        "config_file_name", [("ConfigureScan_4_0_CORR.json"),
                             ("ConfigureScan_basic_CORR.json")]
    )  
    def test_Valid_Configuration_Version(
            self:TestScanConfigurationValidator,
            config_file_name: str):
        path_to_test_json = os.path.join(file_path,config_file_name)
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator:ScanConfigurationValidator = ScanConfigurationValidator(json_str, self.logger)
        result_code, msg = validator.validate_input()
        print(msg)
        assert(result_code == True)