from __future__ import annotations

import copy
import json
import os
from logging import getLogger

import pytest

from ska_mid_cbf_mcs.commons.global_enum import FspModes
from ska_mid_cbf_mcs.subarray.scan_configuration_validator import (
    SubarrayScanConfigurationValidator,
)
from ska_mid_cbf_mcs.subarray.subarray_component_manager import (
    CbfSubarrayComponentManager,
)

# Path
FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/../../data/"


class TestScanConfigurationValidator:
    logger = getLogger()

    # Shared self.full_configuration, to be set in before_each
    full_configuration = {}

    @pytest.fixture(autouse=True)
    def before_each(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
    ):
        """
        Before Each fixure, to setup the CbfSubarrayComponentManager and the Scan Configuration
        """

        config_file_name = "ConfigureScan_4_0_CORR.json"
        receptors = ["SKA001", "SKA036", "SKA063", "SKA100"]
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        subarray_component_manager.start_communicating()

        with open(FILE_PATH + "sys_param_4_boards.json") as f:
            sp = f.read()

        subarray_component_manager.update_sys_param(sp)
        subarray_component_manager.assign_vcc(receptors)

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)

    @pytest.mark.parametrize(
        "config_file_name",
        [("ConfigureScan_1_0_CORR.json"), ("ConfigureScan_19_0_CORR.json")],
    )
    def test_Invalid_Configuration_Version(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        config_file_name: str,
    ):
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)
        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert (
            "The version defined in the Scan Configuration is not supported by MCS:"
            in msg
        )
        assert result_code is False

    @pytest.mark.parametrize(
        "config_file_name,\
         receptors",
        [
            (
                "ConfigureScan_4_0_CORR.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            ),
            (
                "ConfigureScan_basic_CORR.json",
                ["SKA001", "SKA036", "SKA063", "SKA100"],
            ),
        ],
    )
    def test_Valid_Configuration_Version(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        config_file_name: str,
        receptors: list[str],
    ):
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        subarray_component_manager.start_communicating()

        with open(FILE_PATH + "sys_param_4_boards.json") as f:
            sp = f.read()
        subarray_component_manager.update_sys_param(sp)

        subarray_component_manager.assign_vcc(receptors)

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert "Scan configuration is valid." in msg
        assert result_code is True

    @pytest.mark.parametrize("subarray_id", [(2), (3), (16)])
    def test_Invalid_Subarray_ID(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        subarray_id: int,
    ):
        self.full_configuration["common"]["subarray_id"] = subarray_id
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert f"subarray_id {subarray_id} not supported." in msg
        assert result_code is False

    @pytest.mark.parametrize("fsp_ids", [[], [1, 2, 3, 4, 5]])
    def test_Invalid_FSP_IDs(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert (
            f"AA 0.5 only support fsp_ids with array length of 1-4,size of the fsp_ids given: {len(fsp_ids)}"
            in msg
        )
        assert result_code is False

    @pytest.mark.parametrize("fsp_ids", [[5, 6, 7, 8], [15, 19, 23, 27]])
    def test_Invalid_FSP_IDs_CORR_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        fsp_ids: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = f"AA 0.5 Requirment: {(FspModes.CORR).name} Supports only FSP {[1, 2, 3, 4]}."
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    @pytest.mark.parametrize("fsp_id", [1, 2, 3, 4])
    def test_Invalid_Duplicate_FSP_IDs_in_single_subarray(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
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
        # The FSP provided are all dups, but I want to check that it recognized more than one different values as duplciates
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            1
        ]["fsp_ids"] = [fsp_id, 2, 3, 4]
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert (
            f"FSP ID {fsp_id} already assigned to another Processing Region"
            in msg
        )
        assert result_code is False

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
    def test_Invalid_Common_Keys_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        common_key: str,
        common_key_value: any,
    ):
        self.full_configuration["common"][common_key] = common_key_value
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        print(msg)
        assert result_code is False

    @pytest.mark.parametrize(
        "midcbf_key, midcbf_value",
        [
            ("frequency_band_offset_stream1", 1),
            ("frequency_band_offset_stream2", 1),
            ("rfi_flagging_mask", {}),
        ],
    )
    def test_Invalid_MidCBF_Keys_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        midcbf_key: str,
        midcbf_value: any,
    ):
        self.full_configuration["midcbf"][midcbf_key] = midcbf_value
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = f"{midcbf_key} Currently Not Supported In AA 0.5/AA 1.0"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    @pytest.mark.parametrize(
        "start_freq_value", [0, 6719, 1981815360, 1281860161]
    )
    def test_Invalid_start_freq_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        start_freq_value: int,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["start_freq"] = start_freq_value
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "The Processing Region is not within the range for the [0-1981808640] that is acepted by MCS"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    @pytest.mark.parametrize(
        "start_freq_value,channel_count_value",
        [(6720, 3000), (6721, 3000), (1281860160, 3000), (1281860159, 3000)],
    )
    def test_Valid_start_freq_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        start_freq_value: int,
        channel_count_value: int,
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
        ]["output_port"] = output_ports_map
        json_str = json.dumps(self.full_configuration)
        print(
            self.full_configuration["midcbf"]["correlation"][
                "processing_regions"
            ][0]["output_port"]
        )
        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Scan configuration is valid."
        print(msg)
        assert expected_msg in msg
        assert result_code is True

    @pytest.mark.parametrize("fsp_ids", [[1], [1, 2], [1, 2, 3]])
    def test_Invalid_fsp_ids_amount_for_requested_bandwidth_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        fsp_ids: list[int],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["fsp_ids"] = fsp_ids
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Not enough FSP assigned in the processing region to process the range of the requested spectrum"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

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
    def test_Invalid_channel_width_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        channel_width: list[int],
    ):
        # Test cases to be added as more support channel widths are added
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_width"] = channel_width
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = f"Invalid value for channel_width:{channel_width}"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    @pytest.mark.parametrize("channel_count", [-1, 1, 0, 30, 58982, 59000])
    def test_Invalid_channel_count_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        channel_count: int,
    ):
        # Test cases to be added as more support channel widths are added
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = channel_count
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Invalid value for channel_count"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    def test_Invalid_sdp_start_channel_id_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
    ):
        # All three output_x uses the same function.  Just test with one test case should be good enough
        # Test cases to be added as more support channel widths are added
        config_file_name = "ConfigureScan_4_0_CORR.json"
        path_to_test_json = os.path.join(FILE_PATH, config_file_name)

        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"][0][0] = 20

        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_host"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"][0][0] = 20
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_port"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

        with open(path_to_test_json) as file:
            json_str = file.read().replace("\n", "")
        self.full_configuration = json.loads(json_str)
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_link_map"][0][0] = 20
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Start Channel ID (0) must be the same must match the first channel entry of output_link_map"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    @pytest.mark.parametrize(
        "output_host",
        [
            [
                [60, "1.22.3.4"],
                [40, "1.22.3.5"],
                [20, "1.22.3.6"],
                [0, "1.22.3.7"],
            ],
            [
                [0, "1.22.3.4"],
                [40, "1.22.3.5"],
                [40, "1.22.3.6"],
                [60, "1.22.3.7"],
            ],
            [
                [20, "1.22.3.4"],
                [21, "1.22.3.5"],
                [22, "1.22.3.6"],
                [42, "1.22.3.7"],
            ],
        ],
    )
    def test_Invalid_output_host_increment_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
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
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "channel must be in increments of 20"
        print(msg)
        assert expected_msg in msg[1]
        assert result_code is False

    @pytest.mark.parametrize(
        "output_port",
        [
            [[60, 10000], [40, 10001], [20, 1650], [0, 40000]],
            [[0, 10000], [40, 10001], [40, 1650], [60, 40000]],
            [[20, 10000], [21, 10001], [22, 1650], [42, 40000]],
        ],
    )
    def test_Invalid_output_port_increment_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
        output_port: list[list[int, int]],
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = output_port[0][0]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = output_port
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "channel must be in increments of 20"
        print(msg)
        assert expected_msg in msg[1]
        assert result_code is False

    def test_Valid_channel_map_increment_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
    ):
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["sdp_start_channel_id"] = 1
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["channel_count"] = 80
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_port"] = [[1, 10000], [21, 10001], [41, 1650], [61, 40000]]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_host"] = [[1, 10000], [21, 10001], [41, 1650], [61, 40000]]
        self.full_configuration["midcbf"]["correlation"]["processing_regions"][
            0
        ]["output_link_map"] = [[1, 1]]
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "Scan configuration is valid."
        print(msg)
        assert expected_msg in msg
        assert result_code is True

    def test_invalid_channel_map_count_to_single_host_ADR99(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
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
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "There are over 20 channels assigned to a specific port within a single host "
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    def test_invalid_more_channel_in_channel_maps_than_channel_count(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
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
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "output_port exceeds the max allowable channel "
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    # To be removed when MCS supports search window
    def test_reject_search_window(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
    ):
        self.full_configuration["midcbf"]["search_window"] = {}
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "search_window Not Supported in AA 0.5 and AA 1.0"
        print(msg)
        assert expected_msg in msg
        assert result_code is False

    # To be removed when MCS supports vlbi
    def test_reject_vlbi(
        self: TestScanConfigurationValidator,
        subarray_component_manager: CbfSubarrayComponentManager,
    ):
        self.full_configuration["midcbf"]["vlbi"] = {}
        json_str = json.dumps(self.full_configuration)

        validator: SubarrayScanConfigurationValidator = (
            SubarrayScanConfigurationValidator(
                json_str,
                subarray_component_manager._count_fsp,
                subarray_component_manager._proxies_fsp,
                subarray_component_manager._proxies_assigned_vcc,
                subarray_component_manager._proxies_fsp_pss_subarray_device,
                subarray_component_manager._proxies_fsp_pst_subarray_device,
                subarray_component_manager._dish_ids,
                subarray_component_manager._subarray_id,
                self.logger,
            )
        )
        result_code, msg = validator.validate_input()
        expected_msg = "vlbi Currently Not Supported In AA 0.5/AA 1.0"
        print(msg)
        assert expected_msg in msg
        assert result_code is False
