# -*- coding: utf-8 -*-
#
# This file is part of the Mid.CBF MCS project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

"""
TANGO device class for deployment of the Engineering Console
"""

import json

# Additional Imports
import logging
import os
from typing import List

# Tango Imports
from ska_tango_base import SKABaseDevice
from tango import ApiUtil, AttrWriteType
from tango.server import attribute, command, run

# Python Imports
from ska_mid_cbf_mcs.deployer.midcbf_deployer import (
    TalonDxConfig,
    configure_tango_db,
    download_ds_binaries,
    download_fpga_bitstreams,
    generate_talondx_config,
)

__all__ = ["ECDeployer", "main"]

class ECDeployer(SKABaseDevice):
    def init_device(self):
        #TODO: Check logging instantiation
        self.logger_ = logging.getLogger("ec_deployer.py")
        # super().__init__(logger=logger)

    # This is how many boards we can create configurations for currently.
    # Can be increased as needed.
    MAX_BOARDS = 8

    # ----------
    # Attributes
    # ----------

    # read/write spectrum attribute to set talon board indices
    targetTalons = attribute(
        dtype=("int",),
        max_dim_x=MAX_BOARDS,
        access=AttrWriteType.READ_WRITE,
        label="Target Talons",
        doc="Target Talons: Setting Talon Board Indices",
    )

    dsBinaries = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Datastream Binaries",
        doc="Storing ds_binaries JSON data",
    )

    fpgaBitstreams = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="FPGA Bitstreams",
        doc="Storing fpga_bitstreams JSON data",
    )

    # config_commands: for copying into the controller pod to pass the appropriate HPS Master devices
    configCommands = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Config Commands",
        doc="Storing config_commands JSON data",
    )

    # tango_db: for populating the tango database
    tangoDB = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Tango DB",
        doc="Storing tango_db JSON data",
    )

    # ------------------
    # Attributes methods
    # ------------------
    def read_targetTalons(self) -> List[int]:
        return self._target_talons

    def write_targetTalons(self, value: List[int]) -> None:
        self._target_talons = value

    def read_dsBinaries(self) -> str:
        return self._ds_binaries

    def write_dsBinaries(self, value: str) -> None:
        self._ds_binaries = value

    def read_fpgaBitstreams(self) -> str:
        return self._fpga_bitstreams

    def write_fpgaBitstreams(self, value: str) -> None:
        self._fpga_bitstreams = value

    def read_configCommands(self) -> str:
        return self._config_commands

    def write_configCommands(self, value: str) -> None:
        self._config_commands = value

    def read_tangoDB(self) -> str:
        return self._tango_db

    def write_tangoDB(self, value: str) -> None:
        self._tango_db = value

    # --------
    # Commands
    # --------

    @command
    # 4 scripts from boardmap
    def generate_config_jsons(self) -> None:
        self.logger_.info("Generate talondx-config.json file")
        working_dir = "/app/src/ska_mid_cbf_mcs/deployer"
        generate_talondx_config(self.read_targetTalons())
        with open(working_dir + "/talondx_config/ds_binaries.json") as file:
            ds_binaries = json.load(file)
            self._ds_binaries = json.dumps(ds_binaries)

        with open(working_dir + "/talondx_config/fpga_bitstreams.json") as file:
            fpga_bitstreams = json.load(file)
            self._fpga_bitstreams = json.dumps(fpga_bitstreams)

        with open(working_dir + "/talondx_config/config_commands.json") as file:
            config_commands = json.load(file)
            self._config_commands = json.dumps(config_commands)

        with open(working_dir + "/talondx_config/tango_db.json") as file:
            tango_db = json.load(file)
            self._tango_db = json.dumps(tango_db)

    #- aim is for it to be a smart downloader that can understand which binaries have already been downloaded and doesn't redownload if not needed
    @command
    def download_artifacts(self) -> None:
        self.logger_.info("Download Artifacts")
        #TODO: Unhard code this
        os.system("conan remote add ska https://artefact.skatelescope.org/repository/conan-internal/ False")
        os.system("conan remote list")
        os.system("conan --version")

        download_ds_binaries(json.loads(self._ds_binaries), self.logger_)
        download_fpga_bitstreams(
            json.loads(self._fpga_bitstreams), self.logger_
        )

    #- configure the tango DB
    @command
    def configure_db(self) -> None:
        self.logger_.info(
            f'Configure DB - TANGO_HOST = {ApiUtil.get_env_var("TANGO_HOST")}'
        )
        configure_tango_db(json.loads(self._tango_db), self.logger_)


def main(args=None, **kwargs):
    return run((ECDeployer,), args=args, **kwargs)


if __name__ == "__main__":
    main()
