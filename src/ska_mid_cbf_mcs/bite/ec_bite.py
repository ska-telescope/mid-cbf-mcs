import concurrent.futures
import json
import logging
import os

from bite_device_client.bite_client import BiteClient
from ska_tango_base import SKABaseDevice
from tango import AttrWriteType
from tango.server import Device, attribute, command, run

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


# Tango device to handle
class ECBite(SKABaseDevice):
    # -- TANGO DEVICE ATTRIBUTES--
    testID = attribute(
        label="Test ID to run",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        min_value=0,
        fget="get_testID",
        fset="set_testID",
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
        fget="get_biteJSON",
    )

    biteConfig = attribute(
        label="Test type",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="BITE configuration ID. Intended to be used in conjunction with the other CBF input parameter arguments.",
        fget="get_biteConfig",
        fset="set_biteConfig",
    )

    biteInitalTimestampTimeOffset = attribute(
        label="Intial Timestamp Time Offset",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Specifies the initial timestamp time offset for BITE configuration.",
        fget="get_biteInitalTimestampTimeOffset",
        fset="set_biteInitalTimestampTimeOffset",
    )

    packetRateScaleFactor = attribute(
        label="Packet Rate Scale Factor",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Specify the packet rate scale factor",
        fget="get_packetRateScaleFactor",
        fset="set_packetRateScaleFactor",
    )

    inputData = attribute(
        label="Use Input Data",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Specifices a set of CBF input data from cbf_input_data.json ",
        fget="get_inputData",
        fset="set_inputData",
    )

    configMethod = attribute(
        label="Config Method",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Specifies if the users wants to use test # or CBF input data to configure the boards, left blank for default test",
        fget="get_configMethod",
        fset="set_configMethod",
    )

    talonInstance = attribute(
        label="Talon Instance",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Talon instance to test",
        fget="get_talonInstance",
        fset="set_talonInstance",
    )

    biteMacAddress = attribute(
        label="BITE MAC Address",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="The MAC address of the BITE device",
        fget="get_biteMacAddress",
        fset="set_biteMacAddress",
    )

    def init_device(self):
        Device.init_device(self)
        # Set defualt values
        self._testID = "Test_1"
        self._boards = [3]
        self._biteJSON = "cbf_input_data"
        self._biteConfig = "basic gaussian noise"
        self._biteInitalTimestampTimeOffset = 60.0
        self._packetRateScaleFactor = 1.0
        self._inputData = "talon3 basic gaussian noise"
        self._configMethod = ""

        self._talonInstance = ""
        self._biteMacAddress = "00:11:22:33:44:55"

        # Store of boards that we will be testing with
        self._bite_receptors = []
        self.DISH_ID_LUT = {}
        self.K_LUT = {}

        logger_.info("Default config for EC BITE values set")
        # Parse JSON for system configuration
        # Read in JSON config files for testing
        # TODO:Fallbacks for config files not existing
        with open(test_data_path) as f:
            self.test_data = json.load(f)["tests"]
        with open(cbf_input_data_path) as f:
            self.cbf_input_data = json.load(f)["cbf_input_data"]
        with open(bite_configs_path) as f:
            self.bite_config_data = json.load(f)["bite_configs"]

        # Read in configuartion of dish parameters
        with open(
            os.path.join(EXTERNAL_CONFIG_DIR, "initial_system_param.json")
        ) as file:
            self.sys_param = json.loads(file.read())
        for r, v in self.sys_param["dish_parameters"].items():
            self.DISH_ID_LUT[str(v["vcc"])] = r
            self.K_LUT[str(v["vcc"])] = v["k"]

        logger_.info("Config JSON files read successfully")

    # --GETTERS AND SETTERS FOR TANGO DEVICE ATTRIBUTES--
    def set_testID(self, testID):
        self._testID = testID

    def get_testID(self):
        return self._testID

    def set_boards(self, boards):
        self._boards = boards

    def get_boards(self):
        return self._boards

    def get_biteJSON(self):
        return self._biteJSON

    def get_biteConfig(self):
        return self._biteConfig

    def set_biteConfig(self, biteConfig):
        self._biteConfig = biteConfig

    def get_biteInitalTimestampTimeOffset(self):
        return self._biteInitalTimestampTimeOffset

    def set_biteInitalTimestampTimeOffset(self, initalTimestamp):
        self._biteInitalTimestampTimeOffset = initalTimestamp

    def get_packetRateScaleFactor(self):
        return self._packetRateScaleFactor

    def set_packetRateScaleFactor(self, packetRateScaleFactor):
        self._packetRateScaleFactor = packetRateScaleFactor

    def get_inputData(self):
        return self._inputData

    def set_inputData(self, inputData):
        self._inputData = inputData

    def get_configMethod(self):
        return self._configMethod

    def set_configMethod(self, configMethod):
        self._configMethod = configMethod

    def get_talonInstance(self):
        return self._talonInstance

    def set_talonInstance(self, talonInstance):
        self._talonInstance = talonInstance

    def get_biteMacAddress(self):
        return self._biteMacAddress

    def set_biteMacAddress(self, biteMacAddress):
        self._biteMacAddress = biteMacAddress

    # --TANGO DEVICE COMMANDS--

    # Sets up defined boards based on JSON files, using TANGO device attributes to choose file for input
    @command(
        dtype_out=str, doc_out="A list of the currently configured boards"
    )
    def generateBiteData(self):
        # Clear out past config data for fresh generation
        self._bite_receptors = []
        # Generate bite data utilizing the set Tango attributes, for each of the boards sepcified
        # Iterate over boards asked to test with
        # For each board, set dish_id, k, Talon, bite confid id and bite initial timestamp offset
        if self._configMethod == "test":
            logger_.info("Running in test # specification mode")
            self._bite_receptors = self.cbf_input_data.get(
                self.test_data[self._testID]["cbf_input_data"]
            ).get("receptors")

            for b in self._bite_receptors:
                b["k"] = self.bite_config_data.get(b["bite_config_id"])[
                    "sample_rate_k"
                ]
        # Use CBF input data for config
        elif self._configMethod == "input_data":
            logger_.info("Running in input_data specification mode")
            self._bite_receptors = self.cbf_input_data.get(
                self._inputData
            ).get("receptors")
        # Data entry method not given, fall back to default test ID
        else:
            logger_.info("Running with default test ID")
            bite_receptors_template = self.cbf_input_data.get(
                self.test_data[self._testID]["cbf_input_data"]
            ).get("receptors")

            for b in self._boards:
                self._bite_receptors.append(
                    {
                        "dish_id": self.DISH_ID_LUT[str(b)],
                        "k": self.K_LUT[str(b)],
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
                talon_inst=self._talonInstance,
                bite_mac_address=self.biteMacAddress,
            )

        # Spin up threads for each BITE client using config thread funct
        with concurrent.futures.ThreadPoolExecutor() as executor:
            logger_.info("BITE client threads spinup")
            futures = [
                executor.submit(talon_bite_config_thread, receptor)
                for receptor in self._bite_receptors
            ]
            # Await results from each thread
            [f.result() for f in futures]
        returnString = "\n".join(str(e) for e in self._bite_receptors)
        return returnString

    # Starts LSTV replay using a configured bite client
    @command(dtype_out=str)
    def startLSTVReplay(self):
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
            bite.start_lstv_replay(self._packetRateScaleFactor)

        # init biteclient to communicate with board
        # Send command to board to start LSTV replay
        return "Placeholder for command to start lstv replay on target Talons"

    # Stops LSTV replay using a configured bite client
    @command(dtype_out=str)
    def stopLSTVReplay(self):
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
            bite.start_lstv_replay(self._packetRateScaleFactor)
        return "Placeholder for command to stop lstv replay on target Talons"


if __name__ == "__main__":
    run((ECBite,))
