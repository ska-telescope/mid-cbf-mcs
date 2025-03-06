from __future__ import annotations

import json
import os
from logging import getLogger

import pytest

from ska_mid_cbf_mcs.subarray.scan_configuration_validator.validator import (
    SubarrayScanConfigurationValidator,
)

# Path
FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
COUNT_FSP = 8


# TODO: Refactor out CORR only test.  Make it so that this file contains the common tests for all FSP modes
# Example: The Scan configuration this test validatates are ones with multiple FSP mode processing regions
class TestScanConfigurationValidator:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(
        autouse=True,
        params=[
            {
                # Tconfigure_scan_file isn't used in the common test, but kept in to keep it consistant with the FSP Mode specific tests
                "configure_scan_file": "ConfigureScan_4_1_CORR.json",
                "sub_id": 1,
                "dish_ids": [
                    "SKA001",
                    "SKA036",
                    "SKA063",
                    "SKA100",
                    "SKA081",
                    "SKA046",
                    "SKA077",
                    "SKA048",
                ],
            }
        ],
    )
    def validator_params(
        self: TestScanConfigurationValidator,
        request: pytest.FixtureRequest,
    ) -> dict[any]:
        """
        Before Each fixture, to setup the CbfSubarrayComponentManager and the Scan Configuration
        """
        params = request.param

        with open(FILE_PATH + params["configure_scan_file"]) as file:
            json_str = file.read().replace("\n", "")

        self.full_configuration = json.loads(json_str)

        return params

    @pytest.mark.parametrize(
        "config_file_name",
        [
            "ConfigureScan_4_1_CORR.json",
            "ConfigureScan_CORR_PST_8_receptor_5_FSP.json",
            "ConfigureScan_basic_PST_band1.json",
            "ConfigureScan_4_PR_PST.json",
        ],
    )
    def test_Valid_Configuration(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
        config_file_name: str,
    ):
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        assert "Scan configuration is valid." in msg
        assert success is True

    @pytest.mark.parametrize("subarray_id", [(2), (3), (16)])
    def test_Invalid_Subarray_ID(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
        subarray_id: int,
    ):
        self.full_configuration["common"]["subarray_id"] = subarray_id
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        assert f"subarray_id {subarray_id} not supported." in msg
        assert success is False

    @pytest.mark.parametrize(
        "common_key, common_key_value",
        [
            ("band_5_tuning", [5.85, 7.25]),
            ("frequency_band", "3"),
            ("frequency_band", "4"),
            ("frequency_band", "5a"),
            ("frequency_band", "5b"),
        ],
    )
    def test_Invalid_Common_Keys(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
        common_key: str,
        common_key_value: any,
    ):
        self.full_configuration["common"][common_key] = common_key_value
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        assert success is False

    @pytest.mark.parametrize(
        "midcbf_key, midcbf_value",
        [
            ("frequency_band_offset_stream1", 1),
            ("frequency_band_offset_stream2", 1),
            ("rfi_flagging_mask", {}),
        ],
    )
    def test_Invalid_MidCBF_Keys(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
        midcbf_key: str,
        midcbf_value: any,
    ):
        self.full_configuration["midcbf"][midcbf_key] = midcbf_value
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        expected_msg = f"{midcbf_key} Currently Not Supported In AA 0.5/AA 1.0"
        assert expected_msg in msg
        assert success is False

    # To be removed when MCS supports search window
    def test_reject_search_window(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
    ):
        self.full_configuration["midcbf"]["search_window"] = {}
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "search_window Not Supported in AA 0.5 and AA 1.0"
        assert expected_msg in msg
        assert success is False

    # To be removed when MCS supports vlbi
    def test_reject_vlbi(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
    ):
        self.full_configuration["midcbf"]["vlbi"] = {}
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                scan_configuration=json_str,
                dish_ids=validator_params["dish_ids"],
                subarray_id=validator_params["sub_id"],
                logger=self.logger,
                count_fsp=COUNT_FSP,
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "vlbi Currently Not Supported In AA 0.5/AA 1.0"
        assert expected_msg in msg
        assert success is False
