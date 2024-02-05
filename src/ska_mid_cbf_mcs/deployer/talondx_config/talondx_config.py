import json
import os

from jsonschema import validate

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TALON_DX_CONFIG_SCHEMA = os.path.join(THIS_DIR, "talondx-config-schema.json")


class TalonDxConfig:
    """
    TalonDxConfig facilitates loading and validation of the Talon DX
    Configuration JSON file (see schema for details).

    :param config_file: filename of the JSON configuration file
    :type config_file: string
    """

    def __init__(self, config_file):
        self._config_filename = os.path.basename(config_file)
        with open(f"{config_file}", "r") as config_fd:
            self._json = json.load(config_fd)
        with open(TALON_DX_CONFIG_SCHEMA, "r") as schema_fd:
            talon_config_schema = json.load(schema_fd)
        validate(instance=self._json, schema=talon_config_schema)

    def ds_binaries(self):
        """
        Extracts and returns the `"ds_binaries"` section of the configuration file
        that specifies the Tango DS binaries to be downloaded, and where to get them.
        """
        return self._json["ds_binaries"]

    def fpga_bitstreams(self):
        """
        Extracts and returns the `"fpga_bitstreams"` section of the configuration file
        that specifies which FPGA bitstreams to download, and where to get them.
        """
        return self._json["fpga_bitstreams"]

    def config_commands(self):
        """
        Extracts and returns the `"config_commands"` section of the configuration file
        that specifies the configuration commands that are sent from the MCS to the
        Talon DX HPS Master device.
        """
        return self._json["config_commands"]

    def tango_db(self):
        """
        Extracts and returns the `"tango_db"` section of the configuration file that
        contains the device server specifications for populating the Tango DB.
        """
        return self._json["tango_db"]

    def export_config(self, export_path):
        """
        Exports the Talon DX Configuration JSON to a file with same name as that used to
        construct this object. Export will overwrite if the file already exists.

        :param export_path: destination path of exported configuration file.
        :type export_path: string
        """
        with open(
            os.path.join(export_path, self._config_filename), "w+"
        ) as export_fd:
            json.dump(self._json, export_fd, indent=4)
