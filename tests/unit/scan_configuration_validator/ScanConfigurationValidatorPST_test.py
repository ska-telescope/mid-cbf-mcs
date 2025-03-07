from __future__ import annotations

import copy
import json
import os
from logging import getLogger

import pytest

from ska_mid_cbf_mcs.commons.global_enum import (
    FspModes,
    scan_configuration_supported_value,
)
from ska_mid_cbf_mcs.subarray.scan_configuration_validator.validator import (
    SubarrayScanConfigurationValidator,
)

# Path
FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
COUNT_FSP = scan_configuration_supported_value("fsp_ids")[1]


class TestScanConfigurationValidatorPST:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(
        autouse=True,
        params=[
            {
                "configure_scan_file": "ConfigureScan_4_PR_PST.json",
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
        "fsp_ids,error_msg",
        [
            (
                [],
                "AA 1.0 only support fsp_ids with array length of 1-8,size of the fsp_ids given: 0",
            ),
            (
                [5, 6, 7, 8, 9],
                "Too many FSP assigned in the processing region to process the range of the requested spectrum",
            ),
        ],
    )
    def test_Invalid_FSP_IDs(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        fsp_ids: int,
        error_msg: str,
    ):
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        pst_pr["fsp_ids"] = fsp_ids

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
        assert error_msg in msg
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
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_id", [5, 6, 7, 8])
    def test_Invalid_Duplicate_FSP_IDs_in_single_subarray(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        fsp_id: int,
    ):
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        pst_pr["fsp_ids"] = [fsp_id]

        pst_pr1 = pst_config["processing_regions"][1]
        pst_pr1["fsp_ids"] = [fsp_id]
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
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        pst_pr["channel_count"] = channel_count
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

    @pytest.mark.parametrize(
        "config_file_name",
        ["ConfigureScan_basic_PST_band1.json", "ConfigureScan_4_PR_PST.json"],
    )
    def test_Invalid_pst_start_channel_id(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        config_file_name: str,
    ):
        # All three output_x uses the same function.  Just test with one test case should be good enough
        # Test cases to be added as more support channel widths are added
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)

        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_start_channel_id = pst_pr["pst_start_channel_id"]

        pst_pr["timing_beams"][0]["output_host"][0][0] = 185

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
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"][0]["output_port"][0][0] = 185

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
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"][0]["output_link_map"][0][0] = 185

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
        [([[5522, 1]], True), ([[5522, 1], [5707, 2]], False)],
    )
    def test_single_output_link_map_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"][0]["output_link_map"] = mapping

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
        if expected_success_result is False:
            assert "MCS currently only support 1 " in msg
        else:
            assert "Scan configuration is valid." in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "mapping, expected_success_result",
        [([[5522, 20000]], True), ([[5522, 20000], [5707, 20000]], False)],
    )
    def test_single_output_port_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"][0]["output_port"] = mapping

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
        if expected_success_result is False:
            assert "MCS currently only support 1 " in msg
        else:
            assert "Scan configuration is valid." in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "mapping, expected_success_result",
        [
            ([[5522, "192.168.178.26"]], True),
            ([[5522, "192.168.178.26"], [5707, "192.168.178.26"]], False),
        ],
    )
    def test_single_output_host_mapping(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        mapping: list,
        expected_success_result: bool,
    ):
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"][0]["output_host"] = mapping

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
        if expected_success_result is False:
            assert "MCS currently only support 1 " in msg
        else:
            assert "Scan configuration is valid." in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "config_file_name",
        ["ConfigureScan_basic_PST_band1.json", "ConfigureScan_4_PR_PST.json"],
    )
    def test_timing_beam_limitation_per_pr_multi(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        config_file_name,
    ):
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        timing_beams = pst_pr["timing_beams"]

        timing_beam_temp = copy.deepcopy(timing_beams[0])
        timing_beams.append(timing_beam_temp)

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
        expected_message = "MCS currently only support 1 timing beam(s) per PST Processing Region, "
        assert expected_message in msg
        assert success is False

    @pytest.mark.parametrize(
        "config_file_name",
        ["ConfigureScan_basic_PST_band1.json", "ConfigureScan_4_PR_PST.json"],
    )
    def test_timing_beam_limitation_per_pr_none(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        config_file_name,
    ):
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]

        pst_pr["timing_beams"] = []

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
        expected_message = "At least one timing beam must be given for a PST Processgion Region, none was given"
        assert expected_message in msg
        assert success is False

    @pytest.mark.parametrize(
        "start_freq,expected_success_result",
        [
            (296862720, True),
            (495075840, True),
            (693235200, True),
            (891448320, True),
            (1089607680, False),
            (1287767040, False),
            (1485980160, False),
            (1684139520, False),
        ],
    )
    def test_timing_beams_supported_band1_start_freq(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        start_freq: int,
        expected_success_result: bool,
    ):
        path_to_test_json = os.path.join(
            FILE_PATH, "ConfigureScan_basic_PST_band1.json"
        )

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        pst_pr["start_freq"] = start_freq

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
        if expected_success_result is False:
            expected_msg = "is not support by MCS for the given band: 1. "
            assert expected_msg in msg
        else:
            assert "Scan configuration is valid." in msg
        assert success is expected_success_result

    @pytest.mark.parametrize(
        "start_freq,expected_success_result",
        [
            (296862720, False),
            (495075840, False),
            (693235200, False),
            (891448320, True),
            (1089607680, True),
            (1287767040, True),
            (1485980160, True),
            (1684139520, True),
        ],
    )
    def test_timing_beams_supported_band2_start_freq(
        self: TestScanConfigurationValidatorPST,
        validator_params: dict[any],
        start_freq: int,
        expected_success_result: bool,
    ):
        path_to_test_json = os.path.join(
            FILE_PATH, "ConfigureScan_basic_PST_band2.json"
        )

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        pst_config = self.full_configuration["midcbf"]["pst_bf"]
        pst_pr = pst_config["processing_regions"][0]
        pst_pr["start_freq"] = start_freq

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
        if expected_success_result is False:
            expected_msg = "is not support by MCS for the given band: 2. "
            assert expected_msg in msg
        else:
            assert "Scan configuration is valid." in msg
        assert success is expected_success_result
