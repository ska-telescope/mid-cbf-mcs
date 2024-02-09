#!/usr/bin/env python3

import argparse
import json
import os
import sys

import jsonref

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
TEST_PARAMS_DIR = os.path.dirname(os.path.abspath(__file__))

TEST_DATA_DIR = os.path.join(TEST_PARAMS_DIR, "cbf_input_data")
BITE_CONFIG_DIR = os.path.join(TEST_DATA_DIR, "bite_config_parameters")
DELAY_MODEL_PACKAGE_DIR = os.path.join(TEST_PARAMS_DIR, "delay_model_package")
ASSIGN_RESOURCES_DIR = os.path.join(TEST_PARAMS_DIR, "assign_resources")
RELEASE_RESOURCES_DIR = os.path.join(TEST_PARAMS_DIR, "release_resources")
CONFIGURE_SCAN_DIR = os.path.join(TEST_PARAMS_DIR, "configure_scan")
SCAN_DIR = os.path.join(TEST_PARAMS_DIR, "scan")
CHECKPOINTS_DIR = os.path.join(TEST_PARAMS_DIR, "checkpoints")

TEST_PARAMS_DIRS = [
    TEST_PARAMS_DIR,
    TEST_DATA_DIR,
    BITE_CONFIG_DIR,
    DELAY_MODEL_PACKAGE_DIR,
    ASSIGN_RESOURCES_DIR,
    RELEASE_RESOURCES_DIR,
    CONFIGURE_SCAN_DIR,
    SCAN_DIR,
    CHECKPOINTS_DIR,
]


def get_bite_config(bite_config_id):
    file = os.path.join(BITE_CONFIG_DIR, "bite_configs.json")
    with open(f"{file}", "r") as fd:
        configs = json.load(fd)["bite_configs"]

    if bite_config_id in configs:
        config = configs[bite_config_id]
        for source in config["sources"]:
            filter_x_id = source["gaussian"]["pol_x"]["filter"]
            filter_x = get_config("filters", filter_x_id, BITE_CONFIG_DIR)
            filter_y_id = source["gaussian"]["pol_y"]["filter"]
            filter_y = get_config("filters", filter_y_id, BITE_CONFIG_DIR)
            source["gaussian"]["pol_x"]["filter"] = {filter_x_id: filter_x}
            source["gaussian"]["pol_y"]["filter"] = {filter_y_id: filter_y}
        return config

    print(f"'{bite_config_id}' not found in {file}")
    return None


def get_cbf_input_data(cbf_input_data_id):
    file = os.path.join(TEST_DATA_DIR, "cbf_input_data.json")
    with open(f"{file}", "r") as fd:
        cbf_input_data = json.load(fd)["cbf_input_data"]

    if cbf_input_data_id in cbf_input_data:
        data = cbf_input_data[cbf_input_data_id]
        for receptor in data["receptors"]:
            bite_config_id = receptor["bite_config_id"]
            bite_config = get_bite_config(bite_config_id)
            receptor["bite_config_id"] = {bite_config_id: bite_config}
        return data

    print(f"'{cbf_input_data_id}' not found in {file}")
    return None


def get_config(config_name, config_id, config_dir):
    file = os.path.join(config_dir, f"{config_name}.json")
    with open(f"{file}", "r") as fd:
        param_config = json.load(fd)[config_name]

    if config_id in param_config:
        return param_config[config_id]

    print(f"'{config_id}' not found in {file}")
    return None


def generate_test_parameters_section(test_id):
    """Returns the parameter section for a given test id"""
    print(f"Generating test parameter section for test id: '{test_id}'...")
    test_summary = get_config("tests", test_id, TEST_PARAMS_DIR)
    try:
        # get cbf_input_data
        cbf_input_data_id = test_summary["cbf_input_data"]
        cbf_input_data = get_cbf_input_data(cbf_input_data_id)
        test_summary["cbf_input_data"] = cbf_input_data

        # get delay_model_package
        delay_model_package_id = test_summary["delay_model_package"]
        delay_model_package = get_config(
            "delay_model_package",
            delay_model_package_id,
            DELAY_MODEL_PACKAGE_DIR,
        )
        test_summary["delay_model_package"] = delay_model_package

        # get assign_resources
        assign_resources_id = test_summary["assign_resources"]
        assign_resources = get_config(
            "assign_resources", assign_resources_id, ASSIGN_RESOURCES_DIR
        )
        test_summary["assign_resources"] = assign_resources

        # get configure_scan
        scan_config_id = test_summary["configure_scan"]
        scan_config = get_config(
            "configure_scan", scan_config_id, CONFIGURE_SCAN_DIR
        )
        test_summary["configure_scan"] = scan_config

        # get scan
        scan_id = test_summary["scan"]
        scan = get_config("scan", scan_id, SCAN_DIR)
        test_summary["scan"] = scan

        # get checkpoints
        checkpoints_id = test_summary["checkpoints"]
        checkpoints = get_config(
            "checkpoints", checkpoints_id, CHECKPOINTS_DIR
        )
        test_summary["checkpoints"] = checkpoints

        # get release_resources
        release_resources_id = test_summary["release_resources"]
        release_resources = get_config(
            "release_resources", release_resources_id, RELEASE_RESOURCES_DIR
        )
        test_summary["release_resources"] = release_resources

        return test_summary
    except Exception:
        print(
            f"Error: Couldn't generate test parameter section for test id: '{test_id}'"
        )


def generate_test_parameters_json(
    test_ids=[],
    directory=TEST_PARAMS_DIR,
):
    # data structure for holding test parameters which will be written to file
    test_parameters = {}

    if test_ids == []:
        file = os.path.join(directory, "test_parameters.json")
        if os.path.exists(file):
            os.remove(file)
        tests_file = f"{TEST_PARAMS_DIR}/tests.json"
        with open(f"{tests_file}", "r") as fd:
            tests = jsonref.load(fd)["tests"]
        for test_id, _ in tests.items():
            test_parameters[test_id] = generate_test_parameters_section(
                test_id
            )
    else:
        file = os.path.join(directory, "test_parameters_subset.json")
        if os.path.exists(file):
            os.remove(file)
        for test_id in test_ids:
            test_parameters[test_id] = generate_test_parameters_section(
                test_id
            )

    # generate the test parameters json file
    test_json = json.dumps(test_parameters, indent=2)
    with open(f"{file}", "a") as fd:
        fd.write(test_json)

    print(f"{file} generated")


def generate_feature_file(test_ids=[], directory=TEST_PARAMS_DIR):
    feature = "Mid CBF Signal Chain Verification"
    scenario_outline = "Mid CBF Signal Chain Verification"
    steps = [
        "Given that the observing state of the applicable CBF subarray(s) for <test_id> is/are empty.",
        "When the CBF receives the normal sequence of commands for performing a scan with the test parameters specified for <test_id>",
        "Then the checkpoint(s) in the CBF and visibilities generated by the CBF should meet the expected specification for <test_id>",
        "Then the observing state(s) of the applicable CBF subarray(s) for <test_id> should be returned to empty.",
    ]
    example_fields = [
        "test_id",
    ]
    width = 10
    file = os.path.join(TEST_PARAMS_DIR, "tests.json")
    with open(f"{file}", "r") as fd:
        tests = json.load(fd)["tests"]

    if test_ids == []:
        filename = "signal_chain_verification.feature"
    else:
        filename = "signal_chain_verification_subset.feature"
    file = os.path.join(directory, filename)
    with open(f"{file}", "w") as fd:
        fd.write(f"Feature: {feature}\n")
        fd.write("\n")
        fd.write(f"Scenario Outline: {scenario_outline}\n")
        for step in steps:
            fd.write(f"    {step}\n")

        fd.write("\n")
        fd.write("    Examples:\n")

        fd.write("    |")
        for field in example_fields:
            fd.write(f" {field:<{width}} |")

        for test_id, test_params in tests.items():
            test_params["test_id"] = test_id
            if not test_ids or test_id in test_ids:
                fd.write("\n    |")
                for field in example_fields:
                    fd.write(f" {test_params[field]:<{width}} |")

        fd.write("\n")

    print(f"{file} generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-f",
        action="store_true",
        help="optional flag to generate the feature file. Note that at least one of -f or -t must be specified",
    )
    parser.add_argument(
        "-t",
        action="store_true",
        help="optional flag to generate the test parameters json file. Note that at least one of -f or -t must be specified",
    )
    parser.add_argument(
        "-o",
        dest="output_dir",
        nargs="?",
        default=None,
        help=f"optional argument to specify the output directory to save the test parameters json file and/or feature file in; the default output directory is {os.getcwd()}",
    )
    parser.add_argument(
        "--test_ids",
        dest="test_ids",
        nargs="?",
        default=None,
        help="optional argument to specify the test ids for which to generate the test parameters json file and/or feature file. "
        + "Specify as a comma-separated list with no spaces. For example, add the following argument: "
        + "--test_ids 'Test 1,Test 2,Test 3' to generate the test parameters json file and/or feature file for Test 1, Test 2, and Test 3 only.",
    )

    args = parser.parse_args()
    test_ids = []
    if args.test_ids:
        test_ids = args.test_ids.split(",")
    if args.f:
        if args.output_dir is None:
            generate_feature_file(test_ids=test_ids)
        else:
            generate_feature_file(test_ids=test_ids, directory=args.output_dir)

    if args.t:
        if args.output_dir is None:
            generate_test_parameters_json(test_ids=test_ids)
        else:
            generate_test_parameters_json(
                directory=args.output_dir, test_ids=test_ids
            )

    if (not args.t) and (not args.f):
        print(
            "No flags provided: specify -f to generate the feature file, and/or -t to generate the test parameters json file."
        )
        print(
            "Specify -h or --help to list all options for generating the test parameters json file and/or feature file."
        )
