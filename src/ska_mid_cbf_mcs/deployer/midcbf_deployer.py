#!/usr/bin/env python3
import argparse
import copy
import getpass
import json
import logging
import os
import re
import sys
import tarfile
import zipfile
from collections import OrderedDict

import requests
import tango

from ska_mid_cbf_mcs.deployer.conan_local.conan_wrapper import ConanWrapper
from ska_mid_cbf_mcs.deployer.nrcdbpopulate.dbPopulate import DbPopulate
from ska_mid_cbf_mcs.deployer.talondx_config.talondx_config import (
    TalonDxConfig,
)

LOG_FORMAT = "[talondx.py: line %(lineno)s]%(levelname)s: %(message)s"
WORKING_DIR = "/app/src/ska_mid_cbf_mcs/deployer"

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    OK = "\x1b[6;30;42m"
    FAIL = "\x1b[0;30;41m"
    ENDC = "\x1b[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Version:
    """
    Class to facilitate extracting and comparing version numbers in filenames.

    :param filename: string containing a version substring in the x.y.z format, where x,y,z are numbers.
    """

    def __init__(self, filename):
        [ver_x, ver_y, ver_z] = re.findall("[0-9]+", filename)
        self.X = int(ver_x)
        self.Y = int(ver_y)
        self.Z = int(ver_z)

    def match(self, ver):
        """
        Compare two Version object and return true if the versions match.

        :param ver: Version object being compared to this one.
        """
        return self.X == ver.X and self.Y == ver.Y and self.Z == ver.Z


POWER_SWITCH_USER = os.environ.get("POWER_SWITCH_USER")
POWER_SWITCH_PASS = os.environ.get("POWER_SWITCH_PASS")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
TALONDX_CONFIG_FILE = os.path.join(ARTIFACTS_DIR, "talondx-config.json")
DOWNLOAD_CHUNK_BYTES = 1024

TALONDX_STATUS_OUTPUT_DIR = os.environ.get("TALONDX_STATUS_OUTPUT_DIR")

TALON_UNDER_TEST = os.environ.get("TALON_UNDER_TEST")

GITLAB_PROJECTS_URL = "https://gitlab.drao.nrc.ca/api/v4/projects/"
GITLAB_API_HEADER = {
    "PRIVATE-TOKEN": f'{os.environ.get("GIT_ARTIFACTS_TOKEN")}'
}

NEXUS_API_URL = "https://artefact.skatelescope.org/service/rest/v1/"
RAW_REPO_USER = os.environ.get("RAW_USER_ACCOUNT")
RAW_REPO_PASS = os.environ.get("RAW_USER_PASS")


# Split into 4:
# fpga_bitstreams.json
# ds_binaries.json
# config_commands.json
# tango_db.json
def generate_talondx_config(boards_list):
    """
    Reads and displays the state and status of each HPS Tango device running on the
    Talon DX boards, as specified in the configuration commands -- ref `"config_commands"`
    in four JSON files: fpga_bitstreams, ds_binaries, config_commands, and tango_db.

    :param boards: List of boards to deploy
    :type boards: int
    """
    with open(WORKING_DIR + "/talondx_config/talondx_boardmap.json", "r") as config_map:
        config_map_json = json.load(config_map)
        fpga_bitstreams = {
            "fpga_bitstreams": config_map_json["fpga_bitstreams"]
        }
        ds_binaries = {"ds_binaries": config_map_json["ds_binaries"]}
        config_commands = {}
        tango_db = {}

        talondx_config_commands = []
        for board in boards_list:
            talondx_config_commands.append(
                config_map_json["config_commands"][str(board)]
            )
        config_commands["config_commands"] = talondx_config_commands

        db_servers_list = []
        for db_server in config_map_json["tango_db"]["db_servers"]:
            for board in boards_list:
                db_server_tmp = copy.deepcopy(db_server)
                if db_server["server"] == "dshpsmaster":
                    db_server_tmp["deviceList"][0]["id"] = str(board)
                    if (
                        "TalonStatusFQDN"
                        in db_server_tmp["deviceList"][0]["devprop"]
                    ):
                        db_server_tmp["deviceList"][0]["devprop"][
                            "TalonStatusFQDN"
                        ] = db_server_tmp["deviceList"][0]["devprop"][
                            "TalonStatusFQDN"
                        ].replace(
                            "<device>", "talondx-00" + str(board)
                        )
                if db_server["server"] in [
                    "ska-mid-cbf-vcc-app",
                    "ska-mid-cbf-fsp-app",
                    "dshostlutstage1",
                ]:
                    for device in db_server_tmp["deviceList"]:
                        for devprop in device["devprop"]:
                            if "FQDN" in devprop:
                                device["devprop"][devprop] = device["devprop"][
                                    devprop
                                ].replace(
                                    "<device>", "talondx-00" + str(board)
                                )
                            if "host_lut_stage_2_device_name" in devprop:
                                device["devprop"][devprop] = device["devprop"][
                                    devprop
                                ].replace(
                                    "<device>", "talondx-00" + str(board)
                                )
                if db_server["server"] == "dsrdmarx":
                    db_server_tmp["deviceList"][0]["devprop"][
                        "rdmaTxTangoDeviceName"
                    ] = db_server_tmp["deviceList"][0]["devprop"][
                        "rdmaTxTangoDeviceName"
                    ].replace(
                        "<device>", "talondx-00" + str(board)
                    )
                    db_server_tmp["deviceList"][0]["alias"] = "rx" + str(board)
                if db_server["server"] != "talondx_log_consumer":
                    db_server_tmp["instance"] = config_map_json[
                        "config_commands"
                    ][str(board)]["server_instance"]
                    if db_server["server"] != "dsrdmarx":
                        db_server_tmp["device"] = "talondx-00" + str(board)
                    db_servers_list.append(db_server_tmp)
            if db_server["server"] == "talondx_log_consumer":
                db_server_tmp = copy.deepcopy(db_server)
                db_servers_list.append(db_server_tmp)
        tango_db["tango_db"] = {"db_servers": db_servers_list}

        fpga_bitstreams_file = open(WORKING_DIR + "/talondx_config/fpga_bitstreams.json", "w")
        ds_binaries_file = open(WORKING_DIR + "/talondx_config/ds_binaries.json", "w")
        talondx_config_commands_file = open(WORKING_DIR + "/talondx_config/config_commands.json", "w")
        tango_db_file = open(WORKING_DIR + "/talondx_config/tango_db.json", "w")

        json.dump(fpga_bitstreams, fpga_bitstreams_file, indent=6)
        json.dump(ds_binaries, ds_binaries_file, indent=6)
        json.dump(config_commands, talondx_config_commands_file, indent=6)
        json.dump(tango_db, tango_db_file, indent=6)

        fpga_bitstreams_file.close()
        ds_binaries_file.close()
        talondx_config_commands_file.close()
        tango_db_file.close()


def configure_tango_db(inputjson: dict, logger_):
    """
    Configure the Tango DB with devices specified in the talon-config JSON file.
    :param tango_db: JSON string containing the device server specifications for populating the Tango DB
    """
    inputjson = inputjson.get("db_servers", "")
    # Open bitstream file and load dictionary
    bitstream_f = open(
        "/app/images/ska-mid-cbf-engineering-console-deployer/artifacts/fpga-talon/bin/talon_dx-tdc_base-tdc_vcc_processing.json",
        "r",
    )
    bitstream_json = json.load(bitstream_f)
    templates = bitstream_json["DeTrI"]
    try:
        os.remove("artifacts/device_list.json")
        logger_.info("Removed file [device_list.json]")
    except FileNotFoundError:
        logger_.info("File not found [device_list.json]")

    for server in inputjson:
        # TODO: make schema validation part of the dbPopulate class
        # with open( "./schema/dbpopulate_schema.json", 'r' ) as sch:
        with open("nrcdbpopulate/schema/dbpopulate_schema.json", "r") as sch:
            # schemajson = json.load(sch, object_pairs_hook=OrderedDict)
            json.load(sch, object_pairs_hook=OrderedDict)
            sch.seek(0)

        # try:
        #     logger_.info( "Validation step")
        #     jsonschema.validate( server, schemajson )
        # except ValidationError as error:
        #     handleValidationError( error, server )
        #     exit(1)

        dbpop = DbPopulate(server, templates)

        try:
            device_list = []
            with open("artifacts/device_list.json", "r") as f:
                data = json.load(f)
                for i in data["devices"]:
                    device_list.append(i)
        except FileNotFoundError:
            device_list = []

        # Remove and add to ensure any previous record is overwritten
        dbpop.process(mode="remove")
        dbpop.process(mode="add", device_list=device_list)

        with open("artifacts/device_list.json", "w") as f:
            data = {"devices": device_list}
            json.dump(data, f)


def download_git_artifacts(git_api_url, name):
    response = requests.head(url=git_api_url, headers=GITLAB_API_HEADER)

    if response.status_code == requests.codes.ok:  # pylint: disable=no-member
        total_bytes = int(response.headers["Content-Length"])

        response = requests.get(
            git_api_url, headers=GITLAB_API_HEADER, stream=True
        )

        ds_artifacts_dir = os.path.join(ARTIFACTS_DIR, name)
        filename = os.path.join(ds_artifacts_dir, "artifacts.zip")
        bytes_downloaded = 0
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as fd:
            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_BYTES
            ):
                fd.write(chunk)
                bytes_downloaded = min(
                    bytes_downloaded + DOWNLOAD_CHUNK_BYTES, total_bytes
                )
                per_cent = round(bytes_downloaded / total_bytes * 100.0)
                logger_.debug(
                    f"Downloading {total_bytes} bytes to {os.path.relpath(filename, PROJECT_DIR)} "
                    f"[{bcolors.OK}{per_cent:>3} %{bcolors.ENDC}]",
                    end="\r",
                )
            logger_.info("")

        logger_.info("Extracting files... ", end="")
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(ds_artifacts_dir)
        logger_.info(f"{bcolors.OK}done{bcolors.ENDC}")
    else:
        logger_.info(
            f"{bcolors.FAIL}status: {response.status_code}{bcolors.ENDC}"
        )


def download_raw_artifacts(api_url, name, filename):
    # TODO: factorize common code with download_git_artifacts
    response = requests.head(url=api_url, auth=(RAW_REPO_USER, RAW_REPO_PASS))

    if response.status_code == requests.codes.ok:  # pylint: disable=no-member
        total_bytes = int(response.headers["Content-Length"])

        response = requests.get(
            api_url, auth=(RAW_REPO_USER, RAW_REPO_PASS), stream=True
        )

        artifacts_dir = os.path.join(ARTIFACTS_DIR, name)
        filename = os.path.join(artifacts_dir, filename)
        bytes_downloaded = 0
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as fd:
            logger_.debug(
                f"Downloading {total_bytes} bytes to {os.path.relpath(filename, PROJECT_DIR)}"
            )
            for chunk in response.iter_content(
                chunk_size=DOWNLOAD_CHUNK_BYTES
            ):
                fd.write(chunk)
                bytes_downloaded = min(
                    bytes_downloaded + DOWNLOAD_CHUNK_BYTES, total_bytes
                )
                per_cent = round(bytes_downloaded / total_bytes * 100.0)
                print(
                    f"Downloading {total_bytes} bytes to {os.path.relpath(filename, PROJECT_DIR)} "
                    f"[{bcolors.OK}{per_cent:>3} %{bcolors.ENDC}]",
                    end="\r",
                )
            print("\n")

        logger_.info("Extracting files... ")
        if tarfile.is_tarfile(filename):
            tar = tarfile.open(filename, "r")
            tar.extractall(artifacts_dir)
            tar.close()
        else:
            with zipfile.ZipFile(filename, "r") as zip_ref:
                zip_ref.extractall(artifacts_dir)
        logger_.info(f"{bcolors.OK}Done extracting files{bcolors.ENDC}")

        # TODO: workaround; request permissions change from systems team
        os.chmod(os.path.join(artifacts_dir, "MANIFEST.skao.int"), 0o644)
    else:
        logger_.info(
            f"{bcolors.FAIL}File extraction failed - status: {response.status_code}{bcolors.ENDC}"
        )


def download_ds_binaries(ds_binaries: dict, logger_, clear_conan_cache=True):
    """
    Downloads and extracts Tango device server (DS) binaries from Conan packages
    or Git pipeline artifacts.

    :param ds_binaries: JSON string specifying which DS binaries to download.
    :param clear_conan_cache: if true, Conan packages are fetched from remote; default true.
    """

    conan = ConanWrapper(ARTIFACTS_DIR)
    logger_.info(f"Conan version: {conan.version()}")
    if clear_conan_cache:
        logger_.info(f"Conan local cache: {conan.search_local_cache()}")
        logger_.info(
            f"Clearing Conan local cache... {conan.clear_local_cache()}"
        )
    logger_.info(f"Conan local cache: {conan.search_local_cache()}")

    for ds in ds_binaries["ds_binaries"]:
        logger_.info(f"DS Binary: {ds['name']}")

        if ds.get("source") == "conan":
            # Download the specified Conan package
            conan_info = ds.get("conan")
            logger_.info(f"Conan info: {conan_info}")
            conan.download_package(
                pkg_name=conan_info["package_name"],
                version=conan_info["version"],
                user=conan_info["user"],
                channel=conan_info["channel"],
                profile=os.path.join(
                    conan.profiles_dir, conan_info["profile"]
                ),
            )
        elif ds.get("source") == "git":
            # Download the artifacts from the latest successful pipeline
            git_info = ds.get("git")
            url = (
                f'{GITLAB_PROJECTS_URL}{git_info["git_project_id"]}/jobs/artifacts/'
                f'{git_info["git_branch"]}/download?job={git_info["git_pipeline_job"]}'
            )
            download_git_artifacts(git_api_url=url, name=ds["name"])
        else:
            logger_.info(f'Error: unrecognized source ({ds.get("source")})')
            exit(-1)

    # Modify the permissions of Artifacts dir so they can be modified/deleted later
    chmod_r_cmd = "chmod -R o=rwx " + ARTIFACTS_DIR
    os.system(chmod_r_cmd)


def download_fpga_bitstreams(fpga_bitstreams: dict, logger_):
    """
    Downloads and extracts FPGA bitstreams from the CAR (Common Artefact Repository),
    or Git pipeline artifacts.

    :param fpga_bitstreams: JSON string specifying which FPGA bitstreams to download.
    """
    for fpga in fpga_bitstreams["fpga_bitstreams"]:
        req_version = Version(fpga["version"])
        if fpga.get("source") == "raw":
            # Download the bitstream from the raw repo in CAR
            raw_info = fpga.get("raw")
            logger_.info(
                f"FPGA bitstream {raw_info['base_filename']}-{fpga['version']}"
            )
            # url = f"{NEXUS_API_URL}search?repository=raw-internal&group=/{raw_info['group']}/*"
            # TODO: update to filter directly on "base_filename"
            url = f"{NEXUS_API_URL}search?repository=raw-internal&group=/"
            response = requests.get(
                url=url, auth=(RAW_REPO_USER, RAW_REPO_PASS)
            )
            download_urls = []
            if (
                response.status_code
                == requests.codes.ok  # pylint: disable=no-member
            ):
                for item in response.json().get("items", []):
                    # logger_.info(f'\nRaw search response item: {item}')
                    for asset in item.get("assets"):
                        download_urls.append(asset.get("downloadUrl"))
            else:
                logger_.info(response)

            for file_url in download_urls:
                logger_.info(f"file_url = {file_url}")
                filename_pattern = (
                    f"{raw_info['base_filename']}-{fpga['version']}.tar.gz"
                )
                logger_.info(f"filename_pattern = {filename_pattern}")
                filenames = re.findall(filename_pattern, file_url)
                logger_.info(f"filenames: {filenames}")
                if filenames.__len__() == 1:
                    logger_.info(filenames[0])
                    version = Version(filenames[0])
                    if version.match(req_version):
                        logger_.info("Versions match - downloading...")
                        download_raw_artifacts(
                            api_url=file_url,
                            name="fpga-talon",
                            filename=filenames[0],
                        )
        else:
            # Download the artifacts from the latest successful Git pipeline
            git_info = fpga["git"]
            url = (
                f'{GITLAB_PROJECTS_URL}{git_info["git_project_id"]}/jobs/artifacts/'
                f'{git_info["git_branch"]}/download?job={git_info["git_pipeline_job"]}'
            )
            logger_.info(f"GitLab API call for bitstream download: {url}")

            # Alternate URL for downloading specific pipeline job
            """
            url = f"{GITLAB_PROJECTS_URL}{git_info['git_project_id']}/jobs/{git_info['git_pipeline_job']}/artifacts"
            logger_.info(f"GitLab API call for bitstream download: {url}")
            # https://gitlab.drao.nrc.ca/SKA/Mid.CBF/FW/persona/tdc_vcc_processing/-/jobs/12180
            """
            download_git_artifacts(
                git_api_url=url, name=f"fpga-{fpga['target']}"
            )


def db_device_check():
    # Add a log handler for stdout because system tests can only read from that stream.
    # stdout is piped to a file while this subprocess is run so logs won't print twice.
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger_.addHandler(handler)

    with open("artifacts/device_list.json", "r") as f:
        data = f.read()
        device_list = json.loads(data)

        for device in device_list["devices"]:
            # These 3 devices aren't currently implemented but will be eventually..
            if (
                ("vcc-band-3" not in device)
                and ("vcc-band-4" not in device)
                and ("vcc-band-5" not in device)
            ):
                try:
                    dev_proxy = tango.DeviceProxy(device)
                    dev_proxy.ping()
                    logger_.debug(
                        f"Successfully pinged DeviceProxy ({device})"
                    )
                except tango.DevFailed as df:
                    for item in df.args:
                        logger_.error(
                            f"Error pinging DeviceProxy {device} : {item.reason} {item.desc}"
                        )
                    continue
    # Destroy log handler so logs don't print twice.
    logger_.removeHandler(handler)


# def slim_mesh_test(mesh_config: str, loopback: bool):
#     logger_.info(f"Mesh test with config file: {mesh_config}")
#     SlimMeshTest().run_mesh_test(
#         mesh_config_filename=mesh_config, serial_loopback=loopback
#     )


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("midcbf_deployer.py")
    logger_.info(f"User: {getpass.getuser()}")
    parser = argparse.ArgumentParser(description="MID CBF Deployer Utility")
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "--config-db",
        help="configure the Tango database with devices specified in talondx-config.json file",
        action="store_true",
    )
    parser.add_argument(
        "--download-artifacts",
        help="download the FPGA bitstreams and Tango DS binaries from the Common Artefact Repository (CAR)",
        action="store_true",
    )
    parser.add_argument(
        "--generate-talondx-config",
        help="Generate talondx config file",
        action="store_true",
    )
    parser.add_argument("--boards", type=str)
    parser.add_argument(
        "--device-check",
        help="checks that the devices added from dbPopulate have been exported",
        action="store_true",
    )
    parser.add_argument(
        "--mesh-test",
        help="creates a mesh of links between SLIM Tx Rx devices and tests links",
        action="store_true",
    )
    parser.add_argument("--mesh-config", type=str)
    parser.add_argument(
        "--loopback",
        help="configures SLIM Links in serial loopback mode",
        type=int,
    )
    args = parser.parse_args()

    if args.config_db:
        logger_.info(
            f'Configure DB - TANGO_HOST = {tango.ApiUtil.get_env_var("TANGO_HOST")}'
        )
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        configure_tango_db(config.tango_db())
    elif args.download_artifacts:
        logger_.info("Download Artifacts")
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        config.export_config(ARTIFACTS_DIR)
        download_ds_binaries(config.ds_binaries())
        download_fpga_bitstreams(config.fpga_bitstreams())
    elif args.generate_talondx_config and args.boards is not None:
        logger_.info("Generate talondx-config.json file")
        generate_talondx_config(args.boards)
    elif args.device_check:
        logger_.info("Check device status:")
        db_device_check()
    elif args.mesh_test:
        if args.loopback == 1:
            logger_.info("Initiating SLIM Mesh Test in serial loopback mode")
            slim_mesh_test(args.mesh_config, True)
        else:
            logger_.info("Initiating SLIM Mesh Test")
            slim_mesh_test(args.mesh_config, False)
    else:
        logger_.info("Hello from Mid CBF Engineering Console!")
