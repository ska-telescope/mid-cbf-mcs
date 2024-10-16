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


class TestScanConfigurationValidator:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(
        autouse=True,
        params=[
            {
                "configure_scan_file": "ConfigureScan_4_1_CORR.json",
                "sub_id": 1,
                "dish_ids": ["SKA001", "SKA036", "SKA063", "SKA100"],
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
        ["ConfigureScan_4_1_CORR.json"],
    )
    def test_Valid_Configuration_Version(
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
            )
        )
        success, msg = validator.validate_input()
        print(msg)
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
            )
        )
        success, msg = validator.validate_input()
        print(msg)
        assert f"subarray_id {subarray_id} not supported." in msg
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[], [1, 2, 3, 4, 5]])
    def test_Invalid_FSP_IDs(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        print(msg)
        assert (
            f"AA 0.5 only support fsp_ids with array length of 1-4,size of the fsp_ids given: {len(fsp_ids)}"
            in msg
        )
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[5, 6, 7, 8], [15, 19, 23, 27]])
    def test_Invalid_FSP_IDs_CORR_post_v4(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = f"AA 0.5 Requirement: {(FspModes.CORR).name} Supports only FSP {[1, 2, 3, 4]}."
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_id", [1, 2, 3, 4])
    def test_Invalid_Duplicate_FSP_IDs_in_single_subarray(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        assert (
            f"FSP ID {fsp_id} already assigned to another Processing Region"
            in msg
        )
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
    def test_Invalid_Common_Keys_post_v4(
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
            )
        )
        success, msg = validator.validate_input()
        print(msg)
        assert success is False

    @pytest.mark.parametrize(
        "midcbf_key, midcbf_value",
        [
            ("frequency_band_offset_stream1", 1),
            ("frequency_band_offset_stream2", 1),
            ("rfi_flagging_mask", {}),
        ],
    )
    def test_Invalid_MidCBF_Keys_post_v4(
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = f"{midcbf_key} Currently Not Supported In AA 0.5/AA 1.0"
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "start_freq_value", [0, 6719, 1981815360, 1281860161]
    )
    def test_Invalid_start_freq_post_v4(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "The Processing Region is not within the range for the [0-1981808640] that is accepted by MCS"
        print(msg)
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
    def test_Valid_start_freq_post_v4(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
        start_freq_value: int,
        channel_count_value: int,
        fsp_ids: list[int],
    ):
        port = 10000
        output_ports_map = []
        for channel in range(0, channel_count_value - 20 + 1, 20):
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Scan configuration is valid."
        print(msg)
        assert expected_msg in msg
        assert success is True

    @pytest.mark.parametrize("fsp_ids", [[1], [1, 2], [1, 2, 3]])
    def test_Invalid_fsp_ids_amount_too_few_for_requested_bandwidth(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Not enough FSP assigned in the processing region to process the range of the requested spectrum"
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("fsp_ids", [[1, 2], [1, 2, 3], [1, 2, 3, 4]])
    def test_Invalid_fsp_ids_amount_too_many_for_requested_bandwidth(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Too many FSP assigned in the processing region to process the range of the requested spectrum"
        print(msg)
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
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = f"Invalid value for channel_width:{channel_width}"
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize("channel_count", [-1, 1, 0, 30, 58982, 59000])
    def test_Invalid_channel_count_post_v4(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Invalid value for channel_count"
        print(msg)
        assert expected_msg in msg
        assert success is False

    def test_Invalid_sdp_start_channel_id(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
    ):
        # All three output_x uses the same function.  Just test with one test case should be good enough
        # Test cases to be added as more support channel widths are added
        config_file_name = "ConfigureScan_4_1_CORR.json"
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_host"
        print(msg)
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_port"
        print(msg)
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_link_map"
        print(msg)
        assert expected_msg in msg
        assert success is False

    @pytest.mark.parametrize(
        "output_host",
        [
            [
                [20, "1.22.3.4"],
                [21, "1.22.3.5"],
                [22, "1.22.3.6"],
                [42, "1.22.3.7"],
            ],
        ],
    )
    def test_Invalid_output_host_non_multiple_20(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "channel must be in multiples of 20"
        print(msg)
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
        self: TestScanConfigurationValidator,
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
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "channel must be in increments of 20"
        assert expected_msg in msg
        assert success is False

    def test_Valid_channel_map_increment(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "Scan configuration is valid."
        print(msg)
        assert expected_msg in msg
        assert success is True

    def test_invalid_channel_map_count_to_single_host(
        self: TestScanConfigurationValidator,
        validator_params: dict[any],
    ):
        test_output_port_map = [[i, 10000] for i in range(0, 421, 20)]

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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "There are over 20 channels assigned to a specific port within a single host "
        print(msg)
        assert expected_msg in msg
        assert success is False

    def test_invalid_more_channel_in_channel_maps_than_channel_count(
        self: TestScanConfigurationValidator,
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "output_port exceeds the max allowable channel "
        print(msg)
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "search_window Not Supported in AA 0.5 and AA 1.0"
        print(msg)
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
            )
        )
        success, msg = validator.validate_input()
        expected_msg = "vlbi Currently Not Supported In AA 0.5/AA 1.0"
        print(msg)
        assert expected_msg in msg
        assert success is False
