from __future__ import annotations

import json
import logging
import math
import os
import os.path
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
import scipy.stats
import tango
import tqdm
from jsonschema import validate
from tango import DeviceProxy

import ska_mid_cbf_mcs.bite.tango_db_ops as tango_db_ops

TEST_PARAMS_DIR = os.path.join(
    os.getcwd(), "ska-mid-cbf-engineering-tests/test_parameters"
)
TEST_DATA_DIR = os.path.join(TEST_PARAMS_DIR, "cbf_input_data")
BITE_CONFIGS_DIR = os.path.join(TEST_DATA_DIR, "bite_config_parameters")
# TODO: Temp alterations to allow mcs to find these files
"""
DEVICE_SERVER_LIST_DIR = os.path.join(
    os.getcwd(),
    "ska-mid-cbf-engineering-console/images/ska-mid-cbf-engineering-console-bite/bite_device_client/json",
)

"""

DEVICE_SERVER_LIST_DIR = os.path.join(
    os.getcwd(),
    "src/ska_mid_cbf_mcs/bite/bite_device_client/json",
)

SCHEMAS_DIR = os.path.join(os.getcwd(), "schemas")
TEST_DATA_SCHEMA_DIR = os.path.join(SCHEMAS_DIR, "cbf_input_data")
BITE_CONFIGS_SCHEMA_DIR = os.path.join(
    TEST_DATA_SCHEMA_DIR, "bite_config_parameters"
)
"""
DEVICE_SERVER_LIST_SCHEMA_DIR = os.path.join(
    os.getcwd(),
    "ska-mid-cbf-engineering-console/images/ska-mid-cbf-engineering-console-bite/bite_device_client/",
)
"""

DEVICE_SERVER_LIST_SCHEMA_DIR = os.path.join(
    os.getcwd(),
    "src/ska_mid_cbf_mcs/bite/bite_device_client/",
)

LOG_FORMAT = (
    "[BiteClient.%(funcName)s: line %(lineno)s]%(levelname)s: %(message)s"
)

# Constants
LSTV_SAMPLES_PER_DDR_WORD = 21
LSTV_DDR_WORD_IN_BYTES = 64
BYTES_IN_GIGABYTES = 2**30  # 2**30 = 1024 x 1024 x 1024
LSTV_START_WORD_ADDR = 0
BASE_SAMPLE_RATE = 3_960_000_000  # Output sample rate = BASE_SAMPLE_RATE + sample_rate_k * FREQUENCY_OFFSET_DELTA_F
FREQUENCY_OFFSET_DELTA_F = 1800
MAX_UINT16 = 65535  # 2^16 - 1
MAX_INT16 = 32767  # 2^15 - 1


class BiteClient:
    """
    Class to configure the low level BITE devices
    """

    # Utility functions.

    def _ceil_pow2(self: BiteClient, val: int) -> int:
        return 2 ** math.ceil(math.log(val, 2))

    def __init__(self: BiteClient, inst: str, log_to_UML: bool) -> None:
        """
        Initialize BITE parameters

        :param inst: name of Talon HPS DS server instance
        :type inst: str
        :param log_to_UML: set to True to print BITE output to UML format
        :type log_to_UML: bool
        """
        logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
        self._log_to_UML = log_to_UML
        self._logger = logging.getLogger("BiteClient")
        self._server_inst = inst
        self._dp_dict = {}
        self._device_servers = None
        self._lstv_seconds = 0
        self._lstv_start_word_addr = 0
        self._lstv_end_word_addr = 0
        self._low_address_allocation = 0
        self._high_address_allocation = 0
        self._sample_rate = BASE_SAMPLE_RATE

    def init(
        self: BiteClient,
        bite_config_id: str,
        bite_configs_path: str,
        filters_path: str,
        freq_offset_k: int,
    ) -> None:
        """
        Initialize the device servers from the device servers parameter file, and the parameters from the system-tests parameter files.
        """

        with open(
            os.path.join(DEVICE_SERVER_LIST_DIR, "device_server_list.json")
        ) as f:
            self._device_servers = json.load(f)

        with open(bite_configs_path) as f:
            self._bite_configs = json.load(f)

        with open(filters_path) as f:
            self._filter_defs = json.load(f)

        # Validate device servers parameter file
        with open(
            (
                os.path.join(
                    DEVICE_SERVER_LIST_SCHEMA_DIR,
                    "device_server_list_schema.json",
                )
            ),
            "r",
        ) as f:
            validate(instance=self._device_servers, schema=json.load(f))

        # Initialize device proxies
        for name in self._device_servers["device_servers"]:
            self._logger.info(f"Creating dps for device server: {name}")
            self._create_dps_for_server(name)
        self._logger.info("Device proxies have been initialized.")

        # Initialize parameters needed for all method functions
        self._bite_config = self._bite_configs["bite_configs"][bite_config_id]
        self._sample_rate = (
            BASE_SAMPLE_RATE + freq_offset_k * FREQUENCY_OFFSET_DELTA_F
        )
        self._lstv_seconds = self._bite_config["lstv_seconds"]

    def configure_bite(
        self: BiteClient,
        dish_id: str,
        talon_inst: str,
        bite_mac_address: str,
        bite_initial_timestamp_time_offset: str,
    ) -> None:
        """
        Configure BITE devices
        """

        self._logger.info("Entering ...")
        if not self._device_servers:
            self._logger.error("init_devices not called")
            return

        try:
            # Stop any previous LSTV replay
            self._write_attribute(self._dp_dict["lstv_pbk"], "run", 0)

            self._logger.info("Writing lstv ip_control")
            # Stop/reset any previous LSTV generation
            self._command_read_write(
                self._dp_dict["lstv_gen"], "ip_control", False
            )
            self._logger.info("read lstv ip_control")
            if self._dp_dict["lstv_gen"].read_attribute("ip_status").value:
                raise Exception("LSTV Generation already in progress.")

            # Configure noise sources
            sources = self._bite_config["sources"]

            # Configure tone sources
            tones = self._bite_config["tone_gens"]

            # If "sources" in the BITE config file is an empty array, i.e. no noise is desired, the BITE client still needs to
            # configure the gaussian noise generator, but with zero pass filters. This is handled here.
            if len(sources) == 0:
                sources.append({})
                sources[0].setdefault("gaussian", {}).setdefault(
                    "pol_x", {}
                ).setdefault("filter", "filter_zero_pass")
                sources[0].setdefault("gaussian", {}).setdefault(
                    "pol_y", {}
                ).setdefault("filter", "filter_zero_pass")

            source_mean_polX = np.zeros(4, dtype=int)
            source_mean_polY = np.zeros(4, dtype=int)
            source_std_polX = np.zeros(4, dtype=int)
            source_std_polY = np.zeros(4, dtype=int)

            for n, source in enumerate(sources):
                for pol, pol_cfg in source["gaussian"].items():
                    pol = pol.replace("_", "")[:-1] + pol[-1].upper()
                    # Write gaussian noise gen attributes for this pol, and this source #, to device proxy dict
                    self._write_attribute(
                        self._dp_dict[f"gn_gen_src_{pol}_{n}"],
                        "noise_mean",
                        pol_cfg.get("noise_mean", 0),
                    )
                    self._write_attribute(
                        self._dp_dict[f"gn_gen_src_{pol}_{n}"],
                        "noise_std",
                        pol_cfg.get("noise_std", 0.5),
                    )
                    self._write_attribute(
                        self._dp_dict[f"gn_gen_src_{pol}_{n}"],
                        "seed_ln",
                        pol_cfg.get("seed", 1234) + ord(pol[-1].upper()),
                    )
                    self._write_attribute(
                        self._dp_dict[f"gn_gen_src_{pol}_{n}"],
                        "seed_cos",
                        pol_cfg.get("seed", 1234) + ord(pol[-1].upper()) + 1,
                    )

                    # Generate filter coefficients for this pol, and this source #, and write them to device proxy dict
                    num_coeffs = self._filter_defs.get("num_taps", 1024)
                    num_taps = num_coeffs - 1 + (num_coeffs % 2)
                    filter = self._filter_defs.get("filters").get(
                        pol_cfg["filter"], "filter_zero_pass"
                    )
                    if isinstance(filter.get("window"), str):
                        window = filter.get("window")
                    elif isinstance(filter.get("window"), dict):
                        window_name = next(iter(filter["window"].keys()))
                        window = (
                            window_name,
                            list(filter["window"][window_name].values())[0],
                        )
                    self._logger.info(
                        f"Configuring FIR filter for {pol} with '{filter.get('description', '(undescribed)')}'."
                    )
                    coeffs = scipy.signal.firwin2(
                        num_taps,
                        filter.get("band_edges", [0.0, 1.0]),
                        filter.get("band_gains", [0.0, 0.0]),
                        window=window,
                    )
                    coeff_bits = self._filter_defs.get("coeff_bits", 16) - 1
                    fxp_coeffs = np.squeeze(
                        np.array((coeffs * (2**coeff_bits - 1)), dtype=int)
                    )
                    # Zero any remaining coefficients.
                    for _ in range(len(coeffs), num_coeffs):
                        fxp_coeffs = np.append(fxp_coeffs, 0)

                    if fxp_coeffs.shape[0] > 0:
                        self._write_attribute(
                            self._dp_dict[f"fir_filt_src_{pol}_{n}"],
                            "filter_coeff",
                            fxp_coeffs,
                        )
                    else:
                        self._logger.error(
                            "Filter coefficient numpy shape incorrect."
                        )

                source_mean_polX[n] = int(
                    MAX_INT16
                    * source["gaussian"]["pol_x"].get("noise_mean", 0)
                )
                source_mean_polY[n] = int(
                    MAX_INT16
                    * source["gaussian"]["pol_y"].get("noise_mean", 0)
                )

                stdScale = 1
                if stdScale > 1:
                    self._logger.warning("std exceeds maximum")
                else:
                    source_std_polX[n] = int(
                        stdScale
                        * MAX_UINT16
                        * source["gaussian"]["pol_x"].get("noise_std", 0.5)
                    )
                if stdScale > 1:
                    self._logger.warning("std exceeds maximum")
                else:
                    source_std_polY[n] = int(
                        stdScale
                        * MAX_UINT16
                        * source["gaussian"]["pol_y"].get("noise_std", 0.5)
                    )

                # Configure polarisation coupler
                rho = sources[n].get("pol_coupling_rho", 0.0)
                self._write_attribute(
                    self._dp_dict[f"pol_coupler_{n}"],
                    "delay_enable",
                    sources[n].get("pol_Y_1_sample_delay", 0),
                )
                self._write_attribute(
                    self._dp_dict[f"pol_coupler_{n}"],
                    "alpha",
                    int(rho * 2**16),
                )
                self._write_attribute(
                    self._dp_dict[f"pol_coupler_{n}"],
                    "beta",
                    int(math.sqrt(1 - rho**2) * 2**16),
                )

            # Configure tone generators / RFI
            for tone in tones:
                for pol in ("X", "Y"):
                    scale = tone.get(f"pol_{pol.lower()}").get("scale", 0.0)
                    frequency = tone.get(f"pol_{pol.lower()}").get("frequency")
                    norm_freq = frequency / self._sample_rate
                    phase_inc = int(norm_freq * 2**32)
                    self._write_attribute(
                        self._dp_dict[f"tone_gen_pol{pol}"],
                        "mag_scale",
                        int(scale * MAX_UINT16),
                    )
                    self._write_attribute(
                        self._dp_dict[f"tone_gen_pol{pol}"],
                        "phase_inc",
                        phase_inc,
                    )

            # Configure LSTV generator
            self._command_read_write(
                self._dp_dict["lstv_gen"], "ip_control", False
            )
            if self._dp_dict["lstv_gen"].read_attribute("ip_status").value:
                raise Exception("LSTV Generation already in progress.")

            # Read in the external memory (DDR4) lower limit and upper limit
            self._low_address_allocation = (
                self._dp_dict["lstv_gen"]
                .read_attribute("low_address_allocation")
                .value
            )
            self._high_address_allocation = (
                self._dp_dict["lstv_gen"]
                .read_attribute("high_address_allocation")
                .value
            )
            self._logger.info(
                f"High address allocation: {self._high_address_allocation}, low address allocation: {self._low_address_allocation}"
            )

            self._lstv_start_word_addr = self._low_address_allocation

            calculated_end_word_addr = 2 * int(2**30) // 64 + (
                self._lstv_seconds
                * self._sample_rate
                // LSTV_SAMPLES_PER_DDR_WORD
                - 1
            )

            # The end word address is whichever is lower of the high_address_allocation and the calculated end_word_address above
            self._lstv_end_word_addr = min(
                calculated_end_word_addr, self._high_address_allocation
            )
            self._logger.info(
                f"Out of the calculated end word address ({calculated_end_word_addr}) and the high address allocation ({self._high_address_allocation}), choosing {self._lstv_end_word_addr} as the end word address for the LSTV generator."
            )

            self._logger.info(
                f"LSTV start address: {self._lstv_start_word_addr * LSTV_DDR_WORD_IN_BYTES / BYTES_IN_GIGABYTES} GiB"
            )

            # LSTV end address = LSTV start address + requested LSTV size
            self._logger.info(
                f"LSTV end address: {(self._lstv_end_word_addr + 1) * LSTV_DDR_WORD_IN_BYTES / BYTES_IN_GIGABYTES} GiB"
            )

            assert self._lstv_end_word_addr > self._lstv_start_word_addr

            self._logger.info(
                f"LSTV size = {(self._lstv_end_word_addr - self._lstv_start_word_addr) * LSTV_SAMPLES_PER_DDR_WORD/1e9:1.3f} billion samples."
            )
            # Allocate memory for LSTV, start address, in units of 64 bytes
            self._write_attribute(
                self._dp_dict["lstv_gen"],
                "ddr4_start_addr",
                self._lstv_start_word_addr,
            )
            self._write_attribute(
                self._dp_dict["lstv_gen"],
                "ddr4_end_addr",
                self._lstv_end_word_addr,
            )

            # Select sources
            source_selector = int(0)
            for n, _ in enumerate(sources):
                source_selector |= 1 << n
            self._command_read_write(
                self._dp_dict["lstv_gen"],
                "source_select",
                source_selector,
            )

            # Select tones
            tone_selector = int(0)
            for n, _ in enumerate(tones):
                tone_selector |= 1 << n
            self._command_read_write(
                self._dp_dict["lstv_gen"],
                "tone_select",
                tone_selector,
            )

            # Receiver gen removed for FPGA image v0.2.2; may be re-included in future
            self._command_read_write(
                self._dp_dict["lstv_gen"], "receiver_select", 0
            )

            self._write_attribute(
                self._dp_dict["lstv_gen"], "source_mean_polX", source_mean_polX
            )
            self._write_attribute(
                self._dp_dict["lstv_gen"], "source_mean_polY", source_mean_polY
            )
            self._write_attribute(
                self._dp_dict["lstv_gen"], "source_std_polX", source_std_polX
            )
            self._write_attribute(
                self._dp_dict["lstv_gen"], "source_std_polY", source_std_polY
            )

            self._command_read_write(
                self._dp_dict["lstv_gen"], "ip_control", True
            )

            # Helper function to determine the length in Bytes, given an address in memory
            def length(addr):
                return (
                    addr - self._lstv_start_word_addr
                ) * LSTV_DDR_WORD_IN_BYTES

            start = time.time()
            lstv_length = length(self._lstv_end_word_addr + 1)
            self._logger.info(
                f"Long sequence test vector is generating with lstv_length = {lstv_length} Bytes."
            )
            last = current = 0

            # Display progress bar
            with tqdm.tqdm(
                desc="LSTV Generation",
                total=lstv_length,
                unit=" Bytes",
                unit_scale=True,
            ) as pbar:
                while (
                    self._dp_dict["lstv_gen"].read_attribute("ip_status").value
                ):
                    last = current
                    current = length(
                        (
                            self._dp_dict["lstv_gen"]
                            .read_attribute("ddr4_current_addr")
                            .value
                        )
                    )
                    pbar.update(current - last)
                    time.sleep(0.5)
                pbar.close()

            # Stop LSTV generation
            end = time.time()
            self._command_read_write(
                self._dp_dict["lstv_gen"], "ip_control", False
            )
            self._logger.info(
                f"Long sequence test vector finished generation, took {end-start:1.1f} seconds."
            )

            # Configure SPFRx Packetizer
            self._command_read_write(
                self._dp_dict["spfrx_pkt"], "bringup", dish_id
            )
            self._write_attribute(
                self._dp_dict["spfrx_pkt"],
                "sample_rate_band12",
                self._sample_rate,
            )
            # Configure local/remote mac if chosen talon for packet capture
            bite_mac_addr = bite_mac_address.replace(":", "")
            bite_mac_addr_hex = int(bite_mac_addr, 16)
            print(
                f"Talon inst is {talon_inst}, server inst is {self._server_inst}"
            )
            if talon_inst == self._server_inst:
                self._write_attribute(
                    self._dp_dict["spfrx_pkt"], "rem_mac", bite_mac_addr_hex
                )
                self._write_attribute(
                    self._dp_dict["spfrx_pkt"], "loc_mac", 0x102233445566
                )

            # Set 100G ethernet port 0 in loopback
            self._command_read_write(self._dp_dict["100g_eth_0"], "bringup", 1)

        except AssertionError as ae:
            self._logger.error(f"{str(ae)}")
        except Exception as e:
            self._logger.error(f"{str(e)}")

    def start_lstv_replay(
        self: BiteClient, packet_rate_scale_factor: float
    ) -> None:
        """
        Start LSTV Replay
        """
        self._logger.info("Entering ...")
        if not self._device_servers:
            self._logger.error("init_devices not called")
            return

        try:
            self._lstv_start_word_addr = (
                self._dp_dict["lstv_gen"]
                .read_attribute("ddr4_start_addr")
                .value
            )

            self._lstv_end_word_addr = (
                self._dp_dict["lstv_gen"].read_attribute("ddr4_end_addr").value
            )

            self._logger.info(
                f"LSTV repeats after {self._lstv_seconds:1.3f} seconds."
            )

            # Hold the dish packet generator in reset
            self._write_attribute(self._dp_dict["lstv_pbk"], "run", 0)
            self._write_attribute(
                self._dp_dict["lstv_pbk"], "sample_rate", self._sample_rate - 1
            )
            ref_clk_freq = (
                self._dp_dict["lstv_pbk"].read_attribute("ref_clk_freq").value
            )

            # Word_rate is a 32b value such that when it is accumulated a change in msb triggers a new word.
            samples_per_cycle = (
                self._sample_rate / ref_clk_freq * packet_rate_scale_factor
            )
            self._logger.info(f"samples_per_cycle = {samples_per_cycle}")
            self._write_attribute(
                self._dp_dict["lstv_pbk"],
                "samples_per_cycle",
                int(samples_per_cycle * 2**32),
            )

            self._write_attribute(
                self._dp_dict["lstv_pbk"],
                "start_utc_time_code",
                int(
                    datetime.utcnow().replace(tzinfo=timezone.utc).timestamp()
                ),
            )

            self._write_attribute(
                self._dp_dict["lstv_pbk"],
                "lstv_start_addr",
                self._lstv_start_word_addr,
            )
            self._write_attribute(
                self._dp_dict["lstv_pbk"],
                "lstv_end_addr",
                self._lstv_end_word_addr,
            )

            self._write_attribute(self._dp_dict["lstv_pbk"], "run", 1)
        except Exception as e:
            self._logger.error(f"{str(e)}")

    def stop_lstv_replay(self: BiteClient) -> None:
        """
        Stop LSTV Replay
        """
        self._logger.info("Entering ...")
        if not self._device_servers:
            self._logger.error("init_devices not called")
            return

        try:
            self._write_attribute(self._dp_dict["lstv_pbk"], "run", 0)
        except Exception as e:
            self._logger.error(f"{str(e)}")

    def _select_input(
        self: BiteClient, jsonSelector: int, n: int, selector: int
    ) -> int:
        if jsonSelector == 1:
            return selector | 0x1 << int(n)
        return selector

    def _command_read_write(
        self: BiteClient,
        dp: tango.DeviceProxy,
        command_name: str,
        input_args=None,
    ) -> None:
        """
        Wrapper function that calls a tango command

        :param dp: the device proxy whose command will be called
        :param command_name: the command name
        :param input_args: the command input arguments (None if the command has no arguments)
        """
        try:
            if self._log_to_UML:
                print(
                    f"BiteClient -> {dp.dev_name()} ** : CMD {command_name}({input_args})"
                )
            else:
                self._logger.info(
                    f"command_read_write({dp.dev_name()}, {command_name}, {input_args})"
                )
            return dp.command_inout(command_name, input_args)
        except Exception as e:
            self._logger.error(str(e))

    def _write_attribute(
        self: BiteClient, dp: tango.DeviceProxy, attr_name: str, attr_val: Any
    ) -> None:
        """
        Wrapper function that writes to a tango device attribute

        :param dp: the device proxy whose attribute we will be writen
        :param attr_name: the name of the attribute to be written
        :param attr_val: the value to be written to the attribute
        """
        self._logger.info("entered write function")
        try:
            if self._log_to_UML:
                print(
                    f"BiteClient -> {dp.dev_name()} ** : {attr_name} = {attr_val})"
                )
            else:
                self._logger.info(
                    f"write_attribute({dp.dev_name()}, {attr_name}, {attr_val})"
                )
            return dp.write_attribute(attr_name, attr_val)
        except Exception as e:
            self._logger.error(str(e))

    def _create_dps_for_server(self: BiteClient, serverName: str) -> None:
        """
        Get a list of device names from the specified device server and create proxies
            for each device name

        :param serverName: the name of the device server
        """

        server_full_name = serverName + "/" + self._server_inst

        db_dev_list = tango_db_ops.get_existing_devs(server_full_name)

        if db_dev_list:
            for db_dev in db_dev_list:
                if self._create_deviceProxy(db_dev):
                    self._logger.info(
                        "Created device proxy for {}".format(db_dev)
                    )
                else:
                    self._logger.error(
                        "Error on creating device proxy for  {}".format(db_dev)
                    )
        else:
            self._logger.error(
                "The server {} is not running".format(serverName)
            )

    def _create_deviceProxy(self: BiteClient, deviceName: str) -> bool:
        """
        Create a device proxy using the device name

        :param deviceName: the name of the device
        """
        try:
            key = deviceName.split("/")[-1]
            self._logger.info(
                "Creating device server for {}".format(deviceName)
            )
            self._dp_dict[key] = DeviceProxy(deviceName)
        except tango.DevFailed as df:
            for item in df.args:
                self._logger.error(
                    f"Failed to create proxy for {deviceName} : {item.reason} {item.desc}"
                )
            return False
        return True
