"""
TANGO Device to interact with bite_device_client,
 in order to configure and orechestrate tests across boards
"""
import concurrent.futures
import json
import logging
import os

from ska_mid_cbf_mcs.bite.bite_device_client.bite_client import BiteClient
from ska_tango_base import SKABaseDevice
from tango import AttrWriteType
from tango.server import attribute, command, run

# Set up the logger to print neatly to terminal
LOG_FORMAT = "[THREAD: %(threadName)s]->[ec_bite.py: line %(lineno)s]%(levelname)s: %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
logger_ = logging.getLogger("midcbf_bite.py")

# Currently assumes this will be run in where the test_parameters repo will be available
# TODO: Find where this file will be run to ensure proper file opens
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PARAMS_DIR = os.path.join(
    os.getcwd(), "ska-mid-cbf-system-tests/test_parameters"
)
CBF_INPUT_DATA_DIR = os.path.join(TEST_PARAMS_DIR, "cbf_input_data")
BITE_CONFIGS_DIR = os.path.join(CBF_INPUT_DATA_DIR, "bite_config_parameters")
JSON_DIR = os.path.join(PROJECT_DIR, "bite_device_client/json")
EXTERNAL_CONFIG_DIR = os.path.join(
    os.getcwd(), "ska-mid-cbf-engineering-console/ext_config"
)


# Point to the JSON config files the system will be using
cbf_input_data_path = os.path.join(CBF_INPUT_DATA_DIR, "cbf_input_data.json")
test_data_path = os.path.join(TEST_PARAMS_DIR, "tests.json")
bite_configs_path = os.path.join(BITE_CONFIGS_DIR, "bite_configs.json")
filters_path = os.path.join(BITE_CONFIGS_DIR, "filters.json")


class ECBite(SKABaseDevice):
    """ 
    TANGO device for handling the configuration and management of BITE tests.
    Allows for users to configure board setup via TANGO attributes, 
    then use JSON files or default test setup to run test data through the boards.
    Can use Test # or string of data config name to pull from JSON files to run specified tests.
    Currently does not allow for writing of test data manually on call.
    """

    """
    def init_device(self):
        self._test_id = "Test_1"
        self._boards = [3]
        self._bite_json = "cbf_input_data"
        self._bite_config = "basic gaussian noise"
        self._bite_inital_timestamp_time_offset = 60.0
        self._packet_rate_scale_factor = 1.0
        self._input_data = "talon3 basic gaussian noise"
        self._config_method = ""
        self._talon_instance = ""
        self._bite_mac_address = "00:11:22:33:44:55"

        # Store of boards that we will be testing with
        self._bite_receptors = []

        self.dish_id_lut = {}
        self.k_lut = {}
    """
    


    # -- TANGO DEVICE ATTRIBUTES--
    test_id = attribute(
        label="Test ID to run",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        min_value=0,
        fget="get_test_id",
        fset="set_test_id",
    )

    Boards = attribute(
        label="Talon board #s",
        dtype=(int,),
        access=AttrWriteType.READ_WRITE,
        max_dim_x=4,
        min_value=0,
        max_value=3,
        doc="List of boards to run tests on",
        fget="get_boards",
        fset="set_boards",
    )

    biteJSON = attribute(
        label="Config JSON file location",
        dtype=str,
        access=AttrWriteType.READ,
        doc="File location to pull JSON to configure tests with",
        fget="get_bite_json",
    )

    bite_config = attribute(
        label="Test type",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="BITE configuration ID. Intended to be used in conjunction with the other CBF input parameter arguments.",
        fget="get_bite_config",
        fset="set_bite_config",
    )

    bite_inital_timestamp_time_offset = attribute(
        label="Intial Timestamp Time Offset",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Specifies the initial timestamp time offset for BITE configuration.",
        fget="get_bite_inital_timestamp_time_offset",
        fset="set_bite_inital_timestamp_time_offset",
    )

    packet_rate_scale_factor = attribute(
        label="Packet Rate Scale Factor",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Specify the packet rate scale factor",
        fget="get_packet_rate_scale_factor",
        fset="set_packet_rate_scale_factor",
    )

    input_data = attribute(
        label="Use Input Data",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Specifices a set of CBF input data from cbf_input_data.json ",
        fget="get_input_data",
        fset="set_input_data",
    )

    config_method = attribute(
        label="Config Method",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Specifies if the users wants to use test # or CBF input data to configure the boards, left blank for default test",
        fget="get_config_method",
        fset="set_config_method",
    )

    talon_instance = attribute(
        label="Talon Instance",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Talon instance to test",
        fget="get_talon_instance",
        fset="set_talon_instance",
    )

    bite_mac_address = attribute(
        label="BITE MAC Address",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="The MAC address of the BITE device",
        fget="get_bite_mac_address",
        fset="set_bite_mac_address",
    )

    def init_device(self):
        SKABaseDevice.init_device(self)
        # Set defualt values
        self._test_id = "Test_1"
        self._boards = [3]
        self._bite_json = "cbf_input_data"
        self._bite_config = "basic gaussian noise"
        self._bite_inital_timestamp_time_offset = 60.0
        self._packet_rate_scale_factor = 1.0
        self._input_data = "talon3 basic gaussian noise"
        self._config_method = ""

        self._talon_instance = ""
        self._bite_mac_address = "00:11:22:33:44:55"

        # Store of boards that we will be testing with
        self._bite_receptors = []
        self.dish_id_lut = {}
        self.k_lut = {}

        logger_.info("Default config for EC BITE values set")
        # Parse JSON for system configuration
        # Read in JSON config files for testing
        # TODO:Fallbacks for config files not existing
        with open(test_data_path, encoding="utf-8") as f:
            self.test_data = json.load(f)["tests"]
        with open(cbf_input_data_path, encoding="utf-8") as f:
            self.cbf_input_data = json.load(f)["cbf_input_data"]
        with open(bite_configs_path, encoding="utf-8") as f:
            self.bite_config_data = json.load(f)["bite_configs"]

        # Read in configuartion of dish parameters
        with open(
            os.path.join(EXTERNAL_CONFIG_DIR, "initial_system_param.json"), encoding="utf-8"
        ) as file:
            self.sys_param = json.loads(file.read())
        for r, v in self.sys_param["dish_parameters"].items():
            self.dish_id_lut[str(v["vcc"])] = r
            self.k_lut[str(v["vcc"])] = v["k"]

        logger_.info("Config JSON files read successfully")

    # --GETTERS AND SETTERS FOR TANGO DEVICE ATTRIBUTES--
    def set_test_id(self, test_id):
        """TANGO function that sets the Test ID to be used for testing for bite devices"""
        self._test_id = test_id

    def get_test_id(self):
        """TANGO function that returns the Test ID to be used for testing for bite devices"""
        return self._test_id

    def set_boards(self, boards):
        """TANGO function that sets the boards to be used for testing"""
        self._boards = boards

    def get_boards(self):
        """TANGO function that returns the boards set to be used for testing"""
        return self._boards

    def get_bite_json(self):
        """TANGO function that returns the JSON file to be used for board config"""
        return self._bite_json

    def get_bite_config(self):
        """TANGO function that returns the test type to be used for testing, sourced from JSON"""
        return self._bite_config

    def set_bite_config(self, bite_config):
        """TANGO function that sets the test type to be used for testing,
          when using the bit config method"""
        self._bite_config = bite_config

    def get_bite_inital_timestamp_time_offset(self):
        """TANGO function that returns the bite timestamp offset default to be used"""
        return self._bite_inital_timestamp_time_offset

    def set_bite_inital_timestamp_time_offset(self, inital_timestamp):
        """TANGO function that sets the bite timestamp offset default to be used"""
        self._bite_inital_timestamp_time_offset = inital_timestamp

    def get_packet_rate_scale_factor(self):
        """TANGO function that returns the packet rate scale factor default to be used"""
        return self._packet_rate_scale_factor

    def set_packet_rate_scale_factor(self, packet_rate_scale_factor):
        """TANGO function that sets the packet rate scale factor default to be used"""
        self._packet_rate_scale_factor = packet_rate_scale_factor

    def get_input_data(self):
        """TANGO function that returns the input data to be used
          if using the input data config mode"""
        return self._input_data

    def set_input_data(self, input_data):
        """TANGO function that sets the input data to be used if using the input data config mode"""
        self._input_data = input_data

    def get_config_method(self):
        """TANGO function that gets the config method string,
          used to choose how to program boards"""
        return self._config_method

    def set_config_method(self, config_method):
        """TANGO function that sets the config method string,
          used to choose how to program boards"""
        self._config_method = config_method

    def get_talon_instance(self):
        """TANGO function that returns the Talon Instance"""
        return self._talon_instance

    def set_talon_instance(self, talon_instance):
        """TANGO function that sets the Talon Instance"""
        self._talon_instance = talon_instance

    def get_bite_mac_address(self):
        """TANGO function that returns the MAC address for the BITE client boards"""
        return self._bite_mac_address

    def set_bite_mac_address(self, bite_mac_address):
        """TANGO function that sets the MAC address for the BITE client boards"""
        self._bite_mac_address = bite_mac_address

    # --TANGO DEVICE COMMANDS--

    @command(
        dtype_out=str, doc_out="A list of the currently configured boards"
    )
    def generate_bite_data(self):
        """ 
        Using the data set in the BITE TANGO device, generates tests to be run on the boards.
        Uses threading to be able to work on multiple boards at once.
        The Config Method set in the BITE device will determine how this data is read in:
        - "test": will use the test # specified in the CBF input data file to generate.
        - "input_data": Will use the cbf string to specify what test data to use.
        - Otherwise, the default test # and data will be used as set on the tango device.
        """
        # Clear out past config data for fresh generation
        self._bite_receptors = []
        # Generate bite data utilizing the set Tango attributes, for each of the boards sepcified
        # Iterate over boards asked to test with
        # For each board, set dish_id, k, Talon, bite confid id and bite initial timestamp offset
        if self._config_method == "test":
            logger_.info("Running in test # specification mode")
            self._bite_receptors = self.cbf_input_data.get(
                self.test_data[self._test_id]["cbf_input_data"]
            ).get("receptors")

            for b in self._bite_receptors:
                b["k"] = self.bite_config_data.get(b["bite_config_id"])[
                    "sample_rate_k"
                ]
        # Use CBF input data for config
        elif self._config_method == "input_data":
            logger_.info("Running in input_data specification mode")
            self._bite_receptors = self.cbf_input_data.get(
                self._input_data
            ).get("receptors")
        # Data entry method not given, fall back to default test ID
        else:
            logger_.info("Running with default test ID")
            bite_receptors_template = self.cbf_input_data.get(
                self.test_data[self._test_id]["cbf_input_data"]
            ).get("receptors")

            for b in self._boards:
                self._bite_receptors.append(
                    {
                        "dish_id": self.dish_id_lut[str(b)],
                        "k": self.k_lut[str(b)],
                        "talon": b,
                        "bite_config_id": bite_receptors_template[0][
                            "bite_config_id"
                        ],
                        "bite_initial_timestamp_time_offset": bite_receptors_template[
                            0
                        ][
                            "bite_initial_timestamp_time_offset"
                        ],
                    }
                )
        logger_.info("BITE Receptors successfully configured!")

        # Threaded function to configure a BITE client
        def talon_bite_config_thread(receptor):
            # Initialize a BITE server using talon number for server name, no UML logging
            bite = BiteClient(f"talon{receptor['talon']}_test", False)
            bite.init(
                bite_config_id=receptor.get("bite_config_id"),
                bite_configs_path=bite_configs_path,
                filters_path=filters_path,
                freq_offset_k=receptor.get("k"),
            )
            logger_.info("BITE client initilized")
            bite.configure_bite(
                dish_id=receptor.get("dish_id"),
                bite_initial_timestamp_time_offset=receptor.get(
                    "bite_initial_timestamp_time_offset"
                ),
                talon_inst=self._talon_instance,
                bite_mac_address=self.bite_mac_address,
            )

        # Spin up threads for each BITE client using config thread funct
        with concurrent.futures.ThreadPoolExecutor() as executor:
            logger_.info("BITE client threads spinup")
            futures = [
                executor.submit(talon_bite_config_thread, receptor)
                for receptor in self._bite_receptors
            ]
            # Await results from each thread
            results = [f.result() for f in futures]
            logger_.info(results)
        return_string = "\n".join(str(e) for e in self._bite_receptors)
        return return_string

    # Starts LSTV replay using a configured bite client
    @command(dtype_out=str)
    def start_lstv_replay(self):
        """Starts LSTV replay for configured boards as chosen in the BITE device"""
        logger_.info("Starting LSTV replay...")
        # Iterate over board clients
        for b, receptor in enumerate(self._bite_receptors):
            # initialize a BITE server using formating for server instance, no UML logging
            bite = BiteClient(
                f"talon{self._bite_receptors[b]['talon']}_test", False
            )
            bite.init(
                bite_config_id=receptor.get("bite_config_id"),
                bite_configs_path=bite_configs_path,
                filters_path=filters_path,
                freq_offset_k=receptor.get(
                    "k",
                ),
            )
            # Call the BITE device command
            bite.start_lstv_replay(self._packet_rate_scale_factor)

        # init biteclient to communicate with board
        # Send command to board to start LSTV replay
        return "Placeholder for command to start lstv replay on target Talons"

    # Stops LSTV replay using a configured bite client
    @command(dtype_out=str)
    def stop_lstv_replay(self):
        """ Stops LSTV replay for configured boards"""
        logger_.info("Stopping LSTV replay...")
        for b, receptor in enumerate(self._bite_receptors):
            # initialize a BITE server using formating for server instance, no UML logging
            bite = BiteClient(
                f"talon{self._bite_receptors[b]['talon']}_test", False
            )
            bite.init(
                bite_config_id=receptor.get("bite_config_id"),
                bite_configs_path=bite_configs_path,
                filters_path=filters_path,
                freq_offset_k=receptor.get(
                    "k",
                ),
            )
            # Call the BITE device command
            bite.start_lstv_replay(self._packet_rate_scale_factor)
        return "Placeholder for command to stop lstv replay on target Talons"


def main(args=None, **kwargs):
    # PROTECTED REGION ID(ECBite.main) ENABLED START #
    return run((ECBite,), args=args, **kwargs)
    # PROTECTED REGION END # // ECBite.main

if __name__ == "__main__":
    main()
