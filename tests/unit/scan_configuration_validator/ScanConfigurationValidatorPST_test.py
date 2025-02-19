from __future__ import annotations

import json
import os
from logging import getLogger

import pytest

from ska_mid_cbf_tdc_mcs.commons.global_enum import FspModes
from ska_mid_cbf_tdc_mcs.subarray.scan_configuration_validator.validator import (
    SubarrayScanConfigurationValidator,
)

# Path
FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
COUNT_FSP = 4


class TestScanConfigurationValidatorPST:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(
        autouse=True,
        params=[
            {
                "configure_scan_file": "ConfigureScan_6_0_PST.json",
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
        self: TestScanConfigurationValidatorPST,
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
        ["ConfigureScan_6_0_PST.json"],
    )
    def test_Valid_Configuration_Version(
        self: TestScanConfigurationValidatorPST,
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
        print(msg)
        assert "Scan configuration is valid." in msg
        assert success is True

    @pytest.mark.parametrize("fsp_ids", [[], [1, 2], [9]])
    def test_Invalid_FSP_IDs(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "fsp_ids"
        ] = fsp_ids
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
        print(msg)
        assert (
            f"AA 1.0 only support fsp_ids with array length of 1-8,size of the fsp_ids given: {len(fsp_ids)}"
            in msg
        )
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[1], [2], [3], [4], [9]])
    def test_Invalid_FSP_IDs_PST(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "fsp_ids"
        ] = fsp_ids
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
        expected_msg = f"AA 1.0 Requirement: {(FspModes.PST).name} Supports only FSP {[5, 6, 7, 8]}."
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_id", [5, 6, 7, 8])
    def test_Invalid_Duplicate_FSP_IDs_in_single_subarray(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        fsp_id: int,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "fsp_ids"
        ] = [fsp_id]

        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][1][
            "fsp_ids"
        ] = [fsp_id]
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
        assert (
            f"FSP ID {fsp_id} already assigned to another Processing Region"
            in msg
        )
        assert success is False

    @pytest.mark.parametrize(
        "start_freq_value", [296862800, 495075940, 693235300, 891448420]
    )
    def test_Invalid_start_freq_pst_limitations_band1(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        start_freq_value: int,
    ):
        self.full_configuration["common"]["frequency_band"] = "1"
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "start_freq"
        ] = start_freq_value
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
        expected_msg = f"is not support by MCS for the given band: {'1'}. "
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "channel_count", [-1, 1, 0, 30, 3699, 3701, 58982, 59000]
    )
    def test_Invalid_channel_count(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        channel_count: int,
    ):
        # Test cases to be added as more support channel widths are added
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "channel_count"
        ] = channel_count
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
        expected_msg = "Invalid value for channel_count"
        assert expected_msg in msg
        assert success is False

    def test_Invalid_pst_start_channel_id(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
    ):
        # All three output_x uses the same function.  Just test with one test case should be good enough
        # Test cases to be added as more support channel widths are added
        config_file_name = "ConfigureScan_6_0_PST.json"
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        pst_start_channel_id = self.full_configuration["midcbf"]["pst_bf"][
            "processing_regions"
        ][0]["pst_start_channel_id"]

        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_host"][0][0] = 185

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
        expected_msg = f"Start Channel ID given for the processing region ({pst_start_channel_id})"
        assert expected_msg in msg
        assert success is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)

        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_port"][0][0] = 185

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
        expected_msg = f"Start Channel ID given for the processing region ({pst_start_channel_id})"
        assert expected_msg in msg
        assert success is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)

        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_link_map"][0][0] = 185

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
        expected_msg = f"Start Channel ID given for the processing region ({pst_start_channel_id})"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "mapping, expected_success_result",
        [([[0, 1]], True), ([[0, 1], [185, 2]], False)],
    )
    def test_single_output_link_map_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_link_map"] = mapping
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
        assert "MCS currently only support 1 " in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "mapping, expected_success_result",
        [([[0, 20000]], True), ([[0, 20000], [185, 20000]], False)],
    )
    def test_single_output_port_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_link_map"] = mapping
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
        assert "MCS currently only support 1 " in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "mapping, expected_success_result",
        [
            ([[0, "192.168.178.26"]], True),
            ([[0, "192.168.178.26"], [185, "192.168.178.26"]], False),
        ],
    )
    def test_single_output_host_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        self.full_configuration["midcbf"]["pst_bf"]["processing_regions"][0][
            "timing_beams"
        ][0]["output_link_map"] = mapping
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
        assert "MCS currently only support 1 " in msg
        assert success is expected_success_result

    def test_timing_beam_limitation_per_pr(
        self: TestScanConfigurationValidatorPST,
    ):
        pass
