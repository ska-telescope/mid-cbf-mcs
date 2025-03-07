from __future__ import annotations

import copy
import json
import os
from logging import getLogger

import pytest

from ska_mid_cbf_mcs.commons.global_enum import FspModes
from ska_mid_cbf_mcs.subarray.scan_configuration_validator.validator import (
    SubarrayScanConfigurationValidator,
)

# Path
FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"
COUNT_FSP = 8


# TODO: Refactor out CORR only test.  Make it so that this file contains the common tests for all FSP modes
# Example: The Scan configuration this test validatates are ones with multiple FSP mode processing regions
class TestScanConfigurationValidatorCorr:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(
        autouse=True,
        params=[
            {
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
        self: TestScanConfigurationValidatorCorr,
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

    @pytest.mark.parametrize("fsp_ids", [[], [1, 2, 3, 4, 5, 6, 7, 8, 9]])
    def test_Invalid_FSP_IDs(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
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
            f"AA 1.0 only support fsp_ids with array length of 1-8,size of the fsp_ids given: {len(fsp_ids)}"
            in msg
        )
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[5, 6, 7, 8], [15, 19, 23, 27]])
    def test_Invalid_FSP_IDs_CORR(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
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
        expected_msg = f"AA 1.0 Requirement: {(FspModes.CORR).name} Supports only FSP {[1, 2, 3, 4]}."
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_id", [1, 2, 3, 4])
    def test_Invalid_Duplicate_FSP_IDs_in_single_subarray(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        fsp_id: int,
    ):
        self.full_configuration["midcbf"]["correlation"][
            "processing_regions"
        ].append(
            copy.deepcopy(
                self.full_configuration["midcbf"]["correlation"][
                    "processing_regions"
                ][0]
            )
        )
        # The FSP provided are all dupes, but I want to check that it recognized more than one different values as duplicates
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            1
        ]["fsp_ids"] = [fsp_id, 2, 3, 4]
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
        "start_freq_value", [0, 6719, 1981815360, 1281860161]
    )
    def test_Invalid_start_freq(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        start_freq_value: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["start_freq"] = start_freq_value
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
        expected_msg = "The Processing Region is not within the range for the [0-1981808640] that is accepted by MCS"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "start_freq_value,channel_count_value,fsp_ids",
        [
            (6720, 3000, [1]),
            (6721, 3000, [1]),
            (1281860160, 3000, [1, 2]),
            (1281860159, 3000, [1, 2]),
        ],
    )
    def test_Valid_start_freq(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        start_freq_value: int,
        channel_count_value: int,
        fsp_ids: list[int],
    ):
        sdp_start_channel_id = self.full_configuration["midcbf"][
            "correlation"
        ]["processing_regions"][0]["sdp_start_channel_id"]
        port = 10000
        output_ports_map = []
        for channel in range(
            4242, sdp_start_channel_id + channel_count_value - 20 + 1, 20
        ):
            temp = [channel, port]
            output_ports_map.append(temp)
            port += 1
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["start_freq"] = start_freq_value
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = channel_count_value
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"] = output_ports_map
        json_str = json.dumps(self.full_configuration)
        print(
            self.full_configuration["midcbf"]["correlation"][
                "processing_regions"
            ][0]["output_port"]
        )
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
        expected_msg = "Scan configuration is valid."
        assert expected_msg in msg
        assert success is True

    @pytest.mark.parametrize("fsp_ids", [[1], [1, 2], [1, 2, 3]])
    def test_Invalid_fsp_ids_amount_too_few_for_requested_bandwidth(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        fsp_ids: list[int],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
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
        expected_msg = "Not enough FSP assigned in the processing region to process the range of the requested spectrum"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[1, 2], [1, 2, 3], [1, 2, 3, 4]])
    def test_Invalid_fsp_ids_amount_too_many_for_requested_bandwidth(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        fsp_ids: list[int],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = 200
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
        expected_msg = "Too many FSP assigned in the processing region to process the range of the requested spectrum"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "channel_width",
        [
            13439,
            13441,
            210,
            420,
            840,
            1680,
            3360,
            6720,
            26880,
            40320,
            53760,
            80640,
            107520,
            161280,
            215040,
            322560,
            416640,
            430080,
            645120,
        ],
    )
    def test_Invalid_channel_width(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        channel_width: list[int],
    ):
        # Test cases to be added as more support channel widths are added
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_width"] = channel_width
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
        expected_msg = f"Invalid value for channel_width:{channel_width}"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("channel_count", [-1, 1, 0, 30, 58982, 59000])
    def test_Invalid_channel_count(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        channel_count: int,
    ):
        # Test cases to be added as more support channel widths are added
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = channel_count
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

    def test_Invalid_sdp_start_channel_id(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
    ):
        # All three output_x uses the same function.  Just test with one test case should be good enough
        # Test cases to be added as more support channel widths are added
        config_file_name = "ConfigureScan_4_1_CORR.json"
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        sdp_start_channel_id = self.full_configuration["midcbf"][
            "correlation"
        ]["processing_regions"][0]["sdp_start_channel_id"]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"][0][0] = 20

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
        expected_msg = f"Start Channel ID given for the processing region ({sdp_start_channel_id})"
        assert expected_msg in msg
        assert success is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"][0][0] = 20
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
        expected_msg = f"Start Channel ID given for the processing region ({sdp_start_channel_id})"
        assert expected_msg in msg
        assert success is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_link_map"][0][0] = 20
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
        expected_msg = f"Start Channel ID given for the processing region ({sdp_start_channel_id})"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "output_host",
        [
            [
                [4242, "1.22.3.4"],
                [5242, "1.22.3.5"],
                [6544, "1.22.3.6"],
                [8242, "1.22.3.7"],
            ],
        ],
    )
    def test_Invalid_output_host_non_multiple_20(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        output_host: list[list[int, str]],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = output_host[0][0]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = output_host
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
        expected_msg = (
            "difference between output_host values must be a multiple of 20"
        )
        assert expected_msg in msg[1]
        assert success is False

    @pytest.mark.parametrize(
        "output_host",
        [
            [
                [0, "1.22.3.4"],
                [40, "1.22.3.5"],
                [40, "1.22.3.6"],
                [60, "1.22.3.7"],
            ],
            [
                [60, "1.22.3.4"],
                [40, "1.22.3.5"],
                [20, "1.22.3.6"],
                [0, "1.22.3.7"],
            ],
        ],
    )
    def test_Invalid_output_host(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        output_host: list[list[int, str]],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = output_host[0][0]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = output_host
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
        expected_msg = "Output Host Values must be in ascending order and cannot be duplicate"
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "output_port",
        [
            [[60, 10000], [40, 10001], [20, 1650], [0, 40000]],
            [[0, 10000], [40, 10001], [40, 1650], [60, 40000]],
            [[20, 10000], [21, 10001], [22, 1650], [42, 40000]],
        ],
    )
    def test_Invalid_output_port_increment(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
        output_port: list[list[int, int]],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = output_port[0][0]

        # This is to make sure that the first channel in the output host matches
        # the sdp_start_channel_id
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = [output_port[0]]

        # set the output port values according to pytest
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"] = output_port
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
        expected_msg = "channel must be in increments of 20"
        assert expected_msg in msg
        assert success is False

    def test_Valid_channel_map_increment(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = 20
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = 80
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = [1]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"] = [[20, 10000], [40, 10001], [60, 1650], [80, 40000]]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = [[20, 10000], [60, 10001]]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_link_map"] = [[20, 1]]
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
        expected_msg = "Scan configuration is valid."
        assert expected_msg in msg
        assert success is True

    def test_invalid_channel_map_count_to_single_host(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
    ):
        sdp_start_channel_id = self.full_configuration["midcbf"][
            "correlation"
        ]["processing_regions"][0]["sdp_start_channel_id"]
        test_output_port_map = [
            [i, 10000]
            for i in range(
                sdp_start_channel_id, sdp_start_channel_id + 421, 20
            )
        ]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"] = test_output_port_map
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
        expected_msg = "There are over 20 channels assigned to a specific port within a single host "
        assert expected_msg in msg
        assert success is False

    def test_invalid_more_channel_in_channel_maps_than_channel_count(
        self: TestScanConfigurationValidatorCorr,
        validator_params: dict[any],
    ):
        channel_count = self.full_configuration["midcbf"]["correlation"][
            "processing_regions"
        ][0]["channel_count"]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = (channel_count - 20)
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
        expected_msg = "output_port exceeds the max allowable channel "
        assert expected_msg in msg
        assert success is False
