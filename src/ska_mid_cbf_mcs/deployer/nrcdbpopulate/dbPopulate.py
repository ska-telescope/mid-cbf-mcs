"""
dbPopulate
A python module intended to allow a TANGO developer to create, modify and destroy instances
of Devices and Device Servers within a TANGO Database for prototyping and testing purposes.

Created on Oct. 30, 2019
Modified Sept 29, 2020

@author: delrizzo
"""

import os
import re

from tango import Database, DbDevInfo


class DbPopulate:
    # id is the unique ID for a given Talon-DX board. This string becomes a component of the
    # unique TANGO identifier for all devices added to the database.
    id = ""

    # dbHost is a string containing the IP address of the TANGO DB to use
    dbHost = ""

    # db is a TANGO Database instance
    db = None

    ##
    # Initialize the class module
    def __init__(self, js, templates):
        # Store the input JSON file as a dict
        self.json = js

        # determine whether we have a default TANGO DB specified in the environment variables.
        # If not specified, exit.
        self.dbHost = os.environ["TANGO_HOST"]
        if not len(self.dbHost) > 0:
            self.printStatus(
                "__init__", "TANGO_HOST environment variable not set."
            )
            exit(0)
        self.printStatus("__init__", f"Detected TANGO_HOST {self.dbHost}")

        self.templates = templates
        self.template_names = list(self.templates.keys())

        # Establish connection to TANGO DB
        self.dbConnect()

    def printStatus(self, funcName, msg):
        """
        Print a formatted status message to the terminal
        """
        print(f"{__class__.__name__} [{funcName:^18s}] : {msg}")

    def dbConnect(self):
        """
        Establishes a connection to the TANGO DB specified by the TANGO_HOST environment
        variable on the host machine.
        """
        if self.dbHost != "":
            self.printStatus(
                "dbConnect",
                f"Establishing connection to TANGO DB {self.dbHost}",
            )
            self.db = Database()
            self.server_list = self.db.get_server_list()
        else:
            self.printStatus("dbConnect", "Unable to detect TANGO DB. Exiting")
            exit(0)

    def printServerList(self):
        if not self.server_list:
            self.printStatus("printServerList", "Server list is empty.")
        else:
            self.printStatus(
                "printServerList", f"Server list for {self.dbHost}:"
            )
            for s in self.server_list:
                print(f"   SERVER: {s}")
                #                instance_list = self.db.get_device_class_list( s )
                instance_list = [
                    dev
                    for dev in self.db.get_device_class_list(s)
                    if "/" in dev and not dev.startswith("dserver")
                ]
                for i in instance_list:
                    print(f"       - {i}")

    def extract(self):
        server_name_list = self.db.get_server_name_list().value_string
        for server_name in server_name_list:
            print(f"Server name: {server_name}")
        # print(server_name_list)
        if not self.server_list:
            self.printStatus("printServerList", "Server list is empty.")
        else:
            self.printStatus(
                "printServerList", f"Server list for {self.dbHost}:"
            )
            # for s in self.server_list:
            # print( f'   SERVER: {s}' )

    #                instance_list = self.db.get_device_class_list( s )
    # instance_list = [dev for dev in self.db.get_device_class_list(s) if '/' in dev and not dev.startswith('dserver')]
    # for i in instance_list:
    # print( f'       - {i}' )

    def deviceName(self, family):
        """
        Returns the composed instance name for a device
        The device name is the unique tango identifier for a database instance of a device server
        The format is device/name/family

        For the purposes of dbpopulate, device and name come frmo the input json.
        Family is provided by the calling method.
        """
        return f'{self.json["device"]}/{self.json["name"]}/{family}'

    def addDevice(self, device, device_list=[]):
        """
        Adds the device instance(s) specified by the JSON 'devices' element
        """
        className = device["class"]

        alias_dict = {}

        if "registerMetadata" in device.keys():
            register_metadata = device["registerMetadata"]
            for register_set in register_metadata["templateDefinitions"]:
                for temp in self.template_names:
                    temp_match = re.match(register_set["regex"], temp)
                    if temp_match is not None:
                        if "aliasPerMatch" in register_set:
                            alias_per_match = register_set["aliasPerMatch"]
                            if len(temp_match.groupdict()) > 0:
                                matched_values = temp_match.groupdict()
                            else:
                                matched_values = {"": ""}
                            for match in matched_values:
                                alias_per_match = alias_per_match.replace(
                                    "{" + match + "}", matched_values[match]
                                )
                            if alias_per_match in alias_dict:
                                alias_dict[alias_per_match].append(
                                    temp_match.string
                                )
                            else:
                                alias_dict[alias_per_match] = [
                                    temp_match.string
                                ]
                        else:
                            if device["alias"] in alias_dict:
                                alias_dict[device["alias"]].append(
                                    temp_match.string
                                )
                            else:
                                alias_dict[device["alias"]] = [
                                    temp_match.string
                                ]
        else:
            alias_dict[device["alias"]] = []

        for alias in alias_dict:
            if device.get("id", None) is not None:
                name = self.deviceName(f'{alias}-{device["id"]}')
            else:
                name = self.deviceName(alias)
            device_info = DbDevInfo()
            device_info.name = name
            device_info._class = className
            device_info.server = (
                f'{self.json["server"]}/{self.json["instance"]}'
            )
            try:
                self.printStatus(
                    "addDevice",
                    f"  Installing device {name} under {className}",
                )
                self.db.add_device(device_info)
                if name not in device_list:
                    device_list.append(name)
                    self.printStatus(
                        "addDevice", f"  Device list updated with {name}"
                    )
                else:
                    self.printStatus(
                        "addDevice", f"  Duplicate device - {name}"
                    )
            except Exception as e:
                self.printStatus(
                    "addDevice", f" *** Unable to create device {name}\n{e}"
                )
            if "devprop" in device.keys():
                try:
                    for property in device["devprop"]:
                        self.printStatus(
                            "addDevice",
                            f'    Adding device property {property}:{device["devprop"][property]}',
                        )
                        self.db.put_device_property(
                            name, {property: device["devprop"][property]}
                        )
                except Exception as e:
                    self.printStatus(
                        "addDevice",
                        f" *** Unable to set device properties for {name}\n{e}",
                    )
            if "registerMetadata" in device.keys():
                mta_offsets = []
                for template in alias_dict[alias]:
                    mnemonic = self.templates[template]["regdef"]["mnemonic"]

                    if className == "DsResamplerDelayTracker":
                        regdef_properties = {}

                        if "G_POL[0]" in template or "E_RDT_POL_X" in template:
                            regdef_properties[
                                "first_order_delay_models_polX_filename"
                            ] = "/dev/mem"
                            regdef_properties[
                                "first_order_delay_models_polX_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]
                        elif (
                            "G_POL[1]" in template or "E_RDT_POL_Y" in template
                        ):
                            regdef_properties[
                                "first_order_delay_models_polY_filename"
                            ] = "/dev/mem"
                            regdef_properties[
                                "first_order_delay_models_polY_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]
                        else:
                            regdef_properties[
                                "resampler_delay_tracker_lw_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            regdef_properties[
                                "resampler_delay_tracker_hp_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            regdef_properties[
                                "resampler_delay_tracker_filename"
                            ] = "/dev/mem"
                            regdef_properties[
                                "resampler_delay_tracker_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]

                    elif className == "DsCorrelator":
                        regdef_properties = dict(
                            {"correlator_filename": "/dev/mem"}
                        )
                        if mnemonic == "correlator_mta":
                            regdef_properties[
                                "correlator_hp_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            mta_offsets.append(
                                self.templates[template]["firmware_offset"]
                            )
                            regdef_properties[
                                "correlator_mta_firmware_offsets"
                            ] = mta_offsets
                            regdef_properties["correlator_mta_num"] = len(
                                mta_offsets
                            )

                        elif mnemonic == "correlator_lta":
                            regdef_properties[
                                "correlator_lw_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            regdef_properties[
                                "correlator_lta_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]
                    elif className == "DsHistogram":
                        regdef_properties = {}
                        if "E_CSR" in template:
                            regdef_properties[f"{mnemonic}_filename"] = (
                                "/dev/mem"
                            )
                            regdef_properties[f"{mnemonic}_bridge_offset"] = (
                                self.templates[template]["bridge_address"]
                            )
                            regdef_properties[
                                f"{mnemonic}_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]
                        elif "E_HIST_POLX" in template:
                            regdef_properties[f"{mnemonic}_polX_filename"] = (
                                "/dev/mem"
                            )
                            regdef_properties[
                                f"{mnemonic}_polX_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            regdef_properties[
                                f"{mnemonic}_polX_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]
                        elif "E_HIST_POLY" in template:
                            regdef_properties[f"{mnemonic}_polY_filename"] = (
                                "/dev/mem"
                            )
                            regdef_properties[
                                f"{mnemonic}_polY_bridge_offset"
                            ] = self.templates[template]["bridge_address"]
                            regdef_properties[
                                f"{mnemonic}_polY_firmware_offset"
                            ] = self.templates[template]["firmware_offset"]

                    elif className in ["DsHostLUTStage1"]:
                        regdef_properties = dict(
                            {
                                f"{mnemonic}_filename": "/dev/mem",
                                "lw_bridge_base_offset": self.templates[
                                    template
                                ]["bridge_address"],
                                f"{mnemonic}_firmware_offset": self.templates[
                                    template
                                ]["firmware_offset"],
                            }
                        )

                    else:
                        regdef_properties = dict(
                            {
                                f"{mnemonic}_filename": "/dev/mem",
                                f"{mnemonic}_bridge_offset": self.templates[
                                    template
                                ]["bridge_address"],
                                f"{mnemonic}_firmware_offset": self.templates[
                                    template
                                ]["firmware_offset"],
                            }
                        )

                    try:
                        regdef_properties[
                            f"{mnemonic}_register_set_version"
                        ] = self.templates[template]["regdef"]["version"]
                        self.printStatus(
                            "addDevice",
                            f"    Adding device property {regdef_properties}",
                        )
                        self.db.put_device_property(name, regdef_properties)
                    except Exception as e:
                        self.printStatus(
                            "addDevice",
                            f" *** Unable to set device properties for {name}\n{e}",
                        )
        return device_list

    def removeDevice(self, device):
        """
        Deletes the device specified by name from the DB
        """
        className = device["class"]

        alias_dict = {}

        if "registerMetadata" in device.keys():
            register_metadata = device["registerMetadata"]
            for register_set in register_metadata["templateDefinitions"]:
                for temp in self.template_names:
                    temp_match = re.match(register_set["regex"], temp)
                    if temp_match is not None:
                        if "aliasPerMatch" in register_set:
                            alias_per_match = register_set["aliasPerMatch"]
                            if len(temp_match.groupdict()) > 0:
                                matched_values = temp_match.groupdict()
                                for match in matched_values:
                                    alias_per_match = alias_per_match.replace(
                                        "{" + match + "}",
                                        matched_values[match],
                                    )
                                if alias_per_match in alias_dict:
                                    alias_dict[alias_per_match].append(
                                        temp_match.string
                                    )
                                else:
                                    alias_dict[alias_per_match] = [
                                        temp_match.string
                                    ]
                        else:
                            if device["alias"] in alias_dict:
                                alias_dict[device["alias"]].append(
                                    temp_match.string
                                )
                            else:
                                alias_dict[device["alias"]] = [
                                    temp_match.string
                                ]
        else:
            alias_dict[device["alias"]] = []

        for alias in alias_dict:
            if device.get("id", None) is not None:
                name = self.deviceName(f'{alias}-{device["id"]}')
            else:
                name = self.deviceName(alias)

            if self.checkForDevice(className, name):
                self.printStatus("removeDevice", f" Removing device {name}")
                self.db.delete_device(name)

            else:
                self.printStatus(
                    "removeDevice", f" Device {name} not found in DB"
                )

    def checkForDevice(self, className, device):
        """
        Checks the DB for an instance of device with the supplied name, registered as a member
        of the specified TANGO device class
        """
        dbList = self.db.get_device_name("*", className)
        return True if (device in dbList) else False

    def process(self, mode="add", device_list=[]):
        """
        Process a JSON configuration input file. This file should contain information regarding
        the TANGO device classes and instances that are to be created. This includes definintion
        of any attribute and/or device properties.
        """
        self.printStatus("process", f"Called in {mode.upper()} mode.")

        for device in self.json["deviceList"]:
            self.printStatus("process", f'Processing {device["class"]}')

            if mode == "add":
                self.addDevice(device, device_list)

            if mode == "remove":
                self.removeDevice(device)
        return device_list
