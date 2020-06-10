Introduction
==============


# Mid CBF MCS

Documentation on the Developer's portal:
[![ReadTheDoc](https://developer.skatelescope.org/projects/mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skatelescope.org/projects/mid-cbf-mcs/en/latest/?badge=latest)

## Table of contents
* [Description](#description)
* [Getting started](#getting-started)
* [Prerequisities](#prerequisities)
* [How to run](#how-to-run)
  * [Add devices](#add-devices)
  * [Start device servers](#start-device-servers)
  * [Configure attribute polling and events](#configure-attribute-polling-and-events)
  * [View containers](#view-containers)
* [GUI](#gui)
* [License](#license)

## Description

The Mid CBF MCS prototype implements at the moment these TANGO device classes:

* `CbfMaster`: Based on the `SKAMaster` class. It represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a set of housekeeping commands.
* `CbfSubarray`: Based on the `SKASubarray` class. It implements commands needed for scan configuration.
    * `SearchWindow`(for SubarrayMulti): Based on the `SKACapability` class. It implements attributes to configure a search window during a scan.
* `Vcc` and `Fsp`: Based on the `SKACapability` class. These implement commands and attributes needed for scan configuration.
* `Vcc` and `Fsp` Capabilities: Based on the `SKACapability` class. These implement state machines to enable/disable certain VCC and FSP functionality for a scan.
    * `VccBand1And2`, `VccBand3`, `VccBand4`, and `VccBand5` specify the operative frequency band of a VCC.
    * `VccSearchWindow` defines a search window for a VCC.
    * `FspCorr`, `FspPss`, `FspPst`, and `FspVlbi` specify the function mode of an FSP.
* `FspCorrSubarray`: Based on the `SKASubarray` class. It implements commands and attributes needed for scan configuration.
* `TmCspSubarrayLeafNodeTest`: Based on the `SKABaseDevice` class. It simulates a TM CSP Subarray Leaf Node, providing regular updates to parameters during scans using a publish-subscribe mechanism.

To cut down on the number of TANGO device servers, some multi-class servers are implemented to run devices of different classes:

* `CbfSubarrayMulti`: Runs a single instance of `CbfSubarray` and two instances of `SearchWindow`.
* `VccMulti`: Runs a single instance of `Vcc`, one instance each of the VCC frequency band capabilities, and two instances of ``VccSearchWindow``.
* `FspMulti`: Runs a single instance of `Fsp`, one instance each of the FSP function mode capabilities, and 16 instances of `FspCorrSubarray`.

At the moment, the device servers implemented are:

* 1 instance of `CbfMaster`.
* 2 instance of `CbfSubarrayMulti`.
* 4 instances of `FspMulti`.
* 4 instances of `VccMulti`.
* One instance of `TmCspSubarrayLeafNodeTest`.

## Getting started

The project can be found in the SKA GitHub repository.

To get a local copy of the project
```
$ git clone https://gitlab.com/ska-telescope/mid-cbf-mcs.git
```

## Prerequisities

* A TANGO development environment properly configured as described in [SKA developer portal](https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html).

## How to run

The Mid CBF MCS prototype runs in a containerised environment; the YAML configuration files ``tango.yml`` and ``mid-cbf-mcs.yml`` define the services needed to run the TANGO devices inside separate Docker containers.

### Add devices

From the project root directory, issue the command
```
$ make interactive
```

This will begin an interactive terminal session within the build context. Next, add the TANGO devices and their properties to the local MySQL database by running
```
$ cd tangods
$ python addDevicesAndProperties.py
```

The interactive session can then be exited by the command
```
$ exit
```

### Start device servers

To build a new image, issue the following command. If the existing image is adequate, this step may be skipped.
```
$ make build
```

To start the containers, run
```
$ make up
```

### Configure attribute polling and events

From the project root directory, again issue the command
```
$ make interactive
```

Then, to configure attribute polling and events in the local DB, run
```
$ cd tangods
$ python configurePollingAndEvents.py
```

The interactive session may then be exited.
```
$ exit
```

### View containers

At the end of the procedure the command
```
$ docker ps -a
```

shows the list of the running containers:

* `midcbf-cbfmaster`: The `CbfMaster` TANGO device server.
* `midcbf-cbfsubarrayxx`ranges from `01` to `02` The 2 instances of the `CbfSubarrayMulti` TANGO device server.
* `midcbf-fspxx`: `xx` ranges from `01` to `04`. The 4 instances of the `FspMulti` TANGO device servers.
* `midcbf-vccxx`: `x` ranges from `01` to `04`. The 4 instances of the `VccMulti` TANGO device servers.
* `midcbf-tmcspsubarrayleafnodetest`: The `TmCspSubarrayLeafNodeTest` TANGO device server.
* `midcbf-rsyslog`: The rsyslog container for the TANGO devices.
* `midcbf-databaseds`: The TANGO DB device server.
* `midcbf-tangodb`: The MySQL database with the TANGO database tables.

## GUI

This prototype provides a graphical user interface, using WebJive, that runs in Docker containers defined in the configuration files `tangogql.yml`, `traefik.yml`, and `webjive.yml`. To use, start the Docker containers, then navigate to `localhost:22484/testdb`. The following credentials can be used:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can be seen and modified, and device commands can be sent, by creating and saving a new dashboard.

## JIVE

JIVE is a graphical user interface that visualizes the devices, servers, and executes device commands. It has more information than the WebJIVE. Here is the procedure to use JIVE:
 
1. From the project root directory:
```
$ make up
```
2. Run the following command

```
$ docker network inspect tangonet
```
3. Find “midcbf-databaseds”, then copy the first part of its IPv4Address 

4. Run the following command:
```
$ export TANGO_HOST=<the address from step 3>:100000
```
5. Run JIVE:
```
$ JIVE
```

## License

See the `LICENSE` file for details.
