# Mid CBF MCS

Documentation on the Developer's portal:
[![ReadTheDoc](https://developer.skatelescope.org/projects/mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skatelescope.org/projects/mid-cbf-mcs/en/latest/?badge=latest)

## Table of contents (TODO)
* [Description](#description)
* [Getting started](#getting-started)
  * [Install a Virtual Machine](#install_VM)
  * [Install Ubuntu](#install_Ubuntu)
  * [Create a Development Environment](#setup_Tango)
  * [Setup Kubernetes](#setup_Kubernetes)
  * [Setup the MCS Software](#setup_MCS)
* [Running the MCS](#run_MCS)
  * [Running Using Kubernetes](#run_Kubernetes)
  * [Running Using Docker Compose](#run_Docker_Compose)
  * [Add devices](#add-devices)
  * [Start device servers](#start-device-servers)
  * [Configure attribute polling and events](#configure-attribute-polling-and-events)
  * [View containers](#view-containers)
* [JIVE GUI - How to Run](#jive-gui)
* [WebJive GUI](#WebJive GUI)
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

The following instruction follow the instructions on the SKA developer’s portal: 

* https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html

and

* https://developer.skatelescope.org/en/latest/development/getting_started.html

*Note*: For the entire skatelescope.org developer's documentation in PDF format see: 

https://developer.skatelescope.org/_/downloads/en/latest/pdf/


### Install a Virtual Machine

1.  Download Virtualbox from: https://www.virtualbox.org/wiki/Downloads

2.  Install Virtualbox


### Install Ubuntu

Download an image of ubuntu 18.04, for example like the following one:

https://sourceforge.net/projects/osboxes/files/v/vb/55-U-u/18.04/18.04.2/18042.64.7z/download

Steps:

1.  Open up the file downloaded from sourceforge for the ubuntu image with 7-zip and extract the “Ubuntu 18.04.2 (64bit).vdi” file into a known directory

2.  Open up the virtual box software and click “new” and run through the setup process, on the Hard Disk option screen choose “use and existing virtual hard disk file” and then choose the VDI file that you extracted in step two.

3.  Run the OS in virtualbox and login to the ubuntu OS. The login screen should show the account “osboxes.org” it will ask for a password, this is a default account the virtual machine creates for you and the password is **“osboxes.org”** (you can change the name and password in account settings once you are logged in”)

*Note* : If you set your own password for the virtual machine, change "ansible_become_pass=osboxes.org" to "ansible_become_pass=your_own_password"

### Create a Development Environment 

Setting up the Development environment, including Tango environment,  is performed using the ansible playbook script. Follow the commands in the yellow box under the 'Creating a Development Environment' section of the https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html web page.

See that page for a list of the applications installed in this way.

#### Notes and Troubleshooting:

*Note 1*: If you already have an older installation don't forget to first to update your local version of the ansible-playbooks repo (pull, checkout or delete and clone again), before running the ansible-playbooks command.

*Note 2*: You may need to precede the ``ansible-playbook`` command (from the commands sequence at the link above) by ``sudo``.

*Note 3*:  Depending on your system, the ``ansible-playbook`` command may take more than one hour to complete.

*Note 4*: If you encounter Python installation problem with the ansible command, try to explicitly specify the python version in the ansible command, for example:
```
$ ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org" -e ansible_python_interpreter=/usr/bin/python3
```

*Note 5*: If you experience other issues with the script ask questions in the #team-system-support slack channel.

### Start the Tango system

Follow the instruction in the section with the same name at https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html.

### Verifying and/or Setting up Kubernetes

For verifying that Kubernetes and Helm have already been install (or for installing), follow the instructions at https://developer.skatelescope.org/en/latest/development/getting_started.html.

Note that Kubernetes does not need to be launched (i.e. execute the command ``minikube start ...``) at this time (see launching Kubernetes under the 'Running using Kubernetes' section).

### Setting Up The MCS Software

The following projects are required:
* mid-cbf-mcs
* lmc-base-classes

To get a local copy of the mid-cbf-mcs project:
```
$ git clone https://gitlab.com/ska-telescope/mid-cbf-mcs.git
```

To install a local copy of the lmc-base-classes project follow the 'Installation steps' of the README in that project, i.e.:

```
$ git clone https://gitlab.com/ska-telescope/lmc-base-classes
$ cd lmc-base-classes
$ sudo 'python3 -m pip install . --extra-index-url https://nexus.engageska-portugal.pt/repository/pypi/simple
```

Note that LMC Base Classes are needed for example when using Pogo to automatically generate Python TANGO code. Pogo will ask for the Base class pogo (.xmi) files. 
Navigate to the Base class folder when it is ask (typically when you run "pogo xxx", and the base class file is not configured). TODO

## Running the Mid CBF MCS

The Mid CBF MCS Tango servers run in a containerised environment.
The default way of running the mid-cbf-mcs Tango device servers is via Kubernetes. Kubernetes replaced Docker Compose as the containers orchestrator of choice for SKA in mid 2020. However, for convenience, this repository still supports Docker Compose as a way of running the servers (see Section Running Using Docker Compose) (as this approach is more lightweight and may be useful as an alternative for development).

### Running Using Kubernetes

Make sure Kubernetes and Helm have been installed (and verified) as described in the 'Setup Kubernetes' section.

1. Launch Kubernetes using the command:

```sudo -E minikube start --vm-driver=none --extra-config=kubelet.resolv-conf=/var/run/systemd/resolve/resolv.conf```

2. From the root of the project, run:

```$ make build```  
```$ cd docker && make up  && make down```
```$ cd ../  && make install-chart```

#### Set the TANGO_HOST

The TANGO_HOST is required in order to run Jive.

1. Display the Kubernetes nodes and images that have been started up:

```$ kubectl get all -n mid-cbf```

2. Use whatever port is displayed in the line generated from the previous command, containing the string ```tango-host-databaseds-from-makefile-test```, for example:

```service/tango-host-databaseds-from-makefile-test   NodePort    10.103.194.174   <none>        10000:30333/TCP ```

3. Set the TANGO_HOST environment variable using the port number in the line above:

```$ export TANGO_HOST=localhost:30333```

Now Jive can be started and the devices inspected (see the 'JIVE GUI' section)

### Running Using Docker Compose

Running the docker containers using Docker Compose requires the following (see https://docs.docker.com/compose/):

* A ``Dockerfile`` file; this file is located in the root of the project.
* One or more ``docker-compose.yml`` type of files: these files are located in the ``docker`` folder. 
* Running one ``docker-compose up`` command for each of the ``.yml`` files in the docker folder; all the  ``docker-compose`` commands are defined in the ``Makefile`` and executed via a ``make up`` command (see steps below).

#### *Start the containers*

To build new images, issue the following command. If the existing image is adequate, this step may be skipped.

```cd docker```
```$ make build```

To start the containers (inside which will run the Tango servers), issue (from the docker directory):

```$ make up```

#### *View the containers*

To list the running containers issue:

``` $ docker ps```

To list all created containers (not only running):

```docker ps -a``` 

To list all created containers but less verbose, run for ex.:

```docker ps -a --format "table {{.ID}}\t{{.Status}}\t{{.Names}}"``` 


This should list the running containers:

* `midcbf-cbfmaster`: The `CbfMaster` TANGO device server.
* `midcbf-cbfsubarrayxx`ranges from `01` to `02` The 2 instances of the `CbfSubarrayMulti` TANGO device server.
* `midcbf-fspxx`: `xx` ranges from `01` to `04`. The 4 instances of the `FspMulti` TANGO device servers.
* `midcbf-vccxx`: `x` ranges from `01` to `04`. The 4 instances of the `VccMulti` TANGO device servers.
* `midcbf-tmcspsubarrayleafnodetest`: The `TmCspSubarrayLeafNodeTest` TANGO device server.
* `midcbf-rsyslog`: The rsyslog container for the TANGO devices.
* `midcbf-databaseds`: The TANGO DB device server.
* `midcbf-tangodb`: The MySQL database with the TANGO database tables.
* etc.

#### *Set the TANGO_HOST*

The TANGO_HOST environment variable is required in order to run Jive (see bellow). To set TANGO HOST, navigate to teh root of the project and run:
```python configJive.py```

Then run the printed command at the command line.

*Note* : This script executes the following:

1. runs: ``$ docker network inspect tangonet``

2. extracts the first part of its IPv4Address of the "midcbf-databaseds"  and concatenates the TANG)_HOST value and esport command.

Now Jive can be started and the devices inspected (see the 'JIVE GUI' section).

## Running JIVE

JIVE is a graphical user interface with which one can browse the Tango Database and visualize the devices, servers, and execute device commands. (Note that via Jive one can get access to more information than with WebJIVE). Here is the procedure to use JIVE:

```$ jive&```

### Configuring scan (todo)

To configure scan with JIVE, the input needs “\” before each quotation mark. Normal JSON file wouldn’t work.
To solve this problem, there are three options:
1. Use a script to generate this specific input. 
Put your JSON file in tangods/CbfSubarray/JIVEconfigscan/scanconfig.json.
Run 
`Python generateJIVE.py`

2. Use the sendConfig device to trigger configure scan with the subarray. Put configuration JSON in tangods/CbfSubarray/sendConfig/config.JSON
3. Manually insert “\” before each quotation mark (not recommended...)


## WebJive GUI (TODO)

Note: WebJive GUI is currently out of date.
This prototype provides a graphical user interface, using WebJive, that runs in Docker containers defined in the configuration files `tangogql.yml`, `traefik.yml`, and `webjive.yml`. To use, start the Docker containers, then navigate to `localhost:22484/testdb`. The following credentials can be used:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can be seen and modified, and device commands can be sent, by creating and saving a new dashboard.


### Add devices (no longer required- TODO, update)

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

### Configure attribute polling and events (not required TODO - update)

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

## License

See the `LICENSE` file for details.
