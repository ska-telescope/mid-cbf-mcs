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

#Additional Imports
import logging
import os
from typing import List

#Python Imports
from midcbf_deployer import (
    TalonDxConfig,
    configure_tango_db,
    download_ds_binaries,
    download_fpga_bitstreams,
    generate_talondx_config,
)

#Tango Imports
from ska_tango_base import SKABaseDevice
from tango import ApiUtil, AttrWriteType
from tango.server import attribute, command, run

PROJECTS_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PROJECTS_DIR, "artifacts")
TALONDX_CONFIG_FILE = os.path.join(ARTIFACTS_DIR, "talondx-config.json")


__all__ = ["ECDeployer", "main"]

#Skabasedevice
class ECDeployer(SKABaseDevice):
    def __init__(self: ECDeployer, logger: logging.Logger) -> None:
        self.logger_ = logging.getLogger("ec_deployer.py")
        super().__init__(logger=logger)


    #This is how many boards we can create configurations for currently.
    #Can be increased as needed.
    MAX_BOARDS = 8

    # ----------
    # Attributes
    # ----------
    
    #read/write spectrum attribute to set talon board indices
    targetTalons = attribute(
        dtype=("int",),
        max_dim_x=MAX_BOARDS,
        access=AttrWriteType.READ_WRITE,
        label="Target Talons",
        doc="Target Talons: Setting Talon Board Indices",
    )

    #Divide the talondx_boardmap.json file into 3 smaller input jsons, store these as attributes:
    #ds_binaries and fpga_bitstreams: for downloading artifacts
    #PULL as a string into each attr at runtime, the commands will parse at runtime
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
    
    #config_commands: for copying into the controller pod to pass the appropriate HPS Master devices
    configCommands = attribute(
        dtype="DevString",
        access=AttrWriteType.READ_WRITE,
        label="Config Commands",
        doc="Storing config_commands JSON data",
    )
    
    #tango_db: for populating the tango database
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
        self._ds_binaries= value
    
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

    #- generate the config jsons, where the flow will be:
    #   - write the target talon board indices to the device's targets attribute
    #   this will be done by the device_proxy using the attribute r/w
    #   - write the json strings to the boardmap attributes
    # THIS MEANS TAKING THE OUTPUTTED JSON AND STORING IT IN THE DEVICE ATTRIBUTE, WOULD THIS BE A NEW ATTRIBUTE?
    #   - use the config_commands map and target talon boards to generate the config_commands json file for the target boards    


    '''
    4. CONAN Networking issue? 
    5. Artifacts??
    6. What the talondxconfig class do
    "Use the config_commands map and target talon boards to generate the config_commands
    JSON file for the target boards"
    > What is this? 1/board we're generating for? Isn't this already in config_commands.json?
    '''
    @command
    #4 scripts from boardmap
    def generate_config_jsons(self) -> None:
        self.logger_.info("Generate talondx-config.json file")
        generate_talondx_config(self.read_targetTalons())
        with open('./talondx_config/ds_binaries.json') as file:
            ds_binaries = json.load(file)
            self._ds_binaries = json.dumps(ds_binaries)
        
        with open('./talondx_config/fpga_bitstreams.json') as file:
            fpga_bitstreams = json.load(file)
            self._fpga_bitstreams = json.dumps(fpga_bitstreams)
        
        with open('./talondx_config/config_commands.json') as file:
            config_commands = json.load(file)
            self._config_commands = json.dumps(config_commands)
        
        with open('./talondx_config/tango_db.json') as file:
            tango_db = json.load(file)
            self._tango_db = json.dumps(tango_db)

    # # #- aim is for it to be a smart downloader that can understand which binaries have already been downloaded and doesn't redownload if not needed
    '''
    WHAT IS /ARTIFACTS/ ???
    RAW_USER_ACCOUNT + RAW_USER_PASS
    '''
    @command
    def download_artifacts(self) -> None:
        self.logger_.info("Download Artifacts")
        download_ds_binaries(json.loads(self._ds_binaries), self.logger_)
        download_fpga_bitstreams(json.loads(self._fpga_bitstreams), self.logger_)
    
    # # # #- configure the tango DB
    # # # #- sends the config_commands json to the CbfController
    # # # #- uses the tango_db json to populate the database
    @command
    def configure_db(self) -> None:
        self.logger_.info(f'Configure DB - TANGO_HOST = {ApiUtil.get_env_var("TANGO_HOST")}')
        configure_tango_db(json.loads(self._tango_db), self.logger_)        


def main(args=None, **kwargs):
    return run((ECDeployer,), args=args, **kwargs)

if __name__ == "__main__":
    main()
