# Mid CBF MCS

Documentation on the Developer's portal:
[![ReadTheDoc](https://developer.skatelescope.org/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skatelescope.org/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)

## Table of contents
* [Description](#description)
* [Getting started](#getting-started)
* [JIVE GUI - How to Run](#jive-gui---how-to-run)
* [Other ways to run](#Other-ways-to-run)
  * [Add devices](#add-devices)
  * [Start device servers](#start-device-servers)
  * [Configure attribute polling and events](#configure-attribute-polling-and-events)
  * [View containers](#view-containers)
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

### Virtual machine
Virtualbox Download: https://www.virtualbox.org/wiki/Downloads

Ubuntu Image Download: https://sourceforge.net/projects/osboxes/files/v/vb/55-U-u/18.04/18.04.2/18042.64.7z/download

Steps:

1.  Install virtual box

2.  Open up file downloaded from sourceforge for the ubuntu image with 7-zip and extract the “Ubuntu 18.04.2 (64bit).vdi” file into a known directory

3.  Open up the virtual box software and click “new” and run through the setup process, on the Hard Disk option screen choose “use and existing virtual hard disk file” and then choose the VDI file that you extracted in step two.

4.  Run the OS in virtualbox and login to the ubuntu OS. The login screen should show the account “osboxes.org” it will ask for a password, this is a default account the virtual machine creates for you and the password is **“osboxes.org”** (you can change the name and password in account settings once you are logged in”)

The project can be found in the SKA GitHub repository.

To get a local copy of the project
```
$ git clone https://gitlab.com/ska-telescope/ska-mid-cbf-mcs.git
```

### Setting up Tango Enviroment

Setting up the tango enviroment is the next step in this starting guide. Most of the enviroment set up is automated and is installed and configured using the ansible playbook script and the docker compose script. These scripts will install the programs and modules listed below:
- python version 3.7
- TANGO-controls ‘9.3.3’
- Visual Studio Code, PyCharm Community Edition
- ZEROMQ ‘4.3.2’
- OMNIORB ‘4.2.3’
Run the following commands in your terminal, it will clone the ansible playbook repository, install it, and then run the script and set up the enviroment, if you experience issues with the script ask questions in the #team-system-support slack channel. The following instruction can be also found at the developer’s portal: https://developer.skatelescope.org/en/latest/tools/tango-devenv-setup.html
```
$ sudo apt -y install git                                                                         
$ git clone https://gitlab.com/ska-telescope/ansible-playbooks                                         
$  cd ansible-playbooks                                                                                        
$  sudo apt-add-repository --yes --update ppa:ansible/ansible && sudo apt -y install ansible                                                                                  
$ ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org"                                                        $ $ sudo reboot
```

Trouble shooting:
- If you set your own password for the virtual machine, change "ansible_become_pass=osboxes.org" to "ansible_become_pass=<your own password"  
- If you encounter python related problem with the ansible command, try to specify the python version with anisible script, for example:
```
$ ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org" -e ansible_python_interpreter=/usr/bin/python2
Using python2 like above may solve the problem for you.
```
### Setting Up LMC Base Classes
LMC Base Classes are needed if you want to use Pogo to generate code. Pogo will ask you for Base class pogo files. 
Find in the Base class folder when it is ask(typically when you run "pogo xxx", and the base class file is not configured)
Install https://gitlab.com/ska-telescope/lmc-base-classes in your /venv/bin/pip directory
> $ git clone https://gitlab.com/ska-telescope/lmc-base-classes                                   
> $ cd lmc-base-classes                                                                                     
> $ sudo /venv/bin/pip install                                                        

## JIVE GUI - How to Run

### starting JIVE
For developer use. JIVE is a graphical user interface that visualizes the devices, servers, and executes device commands. It has more information than the WebJIVE. Here is the procedure to use JIVE:
 
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
**Note: step 2-3 can be automated by running "python configJive.py" script in the main folder**

### Configuring scan

To configure scan with JIVE, the input needs “\” before each quotation mark. Normal JSON file wouldn’t work.
To solve this probelm, there are three options:
1. Use a script to generate this specific input. 
Put your JSON file in tangods/CbfSubarray/JIVEconfigscan/scanconfig.JSON.
Run 
`Python generateJIVE.py`

2. Use the sendConfig device to trigger configure scan with the subarray. Put configuration JSON in tangods/CbfSubarray/sendConfig/config.JSON
3. Manually insert “\” before each quotation mark (not recommended...)




## Other ways to run

The Mid CBF MCS prototype runs in a containerised environment; the YAML configuration files ``tango.yml`` and ``ska-mid-cbf-mcs.yml`` define the services needed to run the TANGO devices inside separate Docker containers.

### Start device servers

To build a new image, issue the following command. If the existing image is adequate, this step may be skipped.
```
$ make build
```

To start the containers, run
```
$ make up
```

You can then view the devices with JIVE. See below on how to activate JIVE.

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



## WebJive GUI

Note: WebJive GUI is currently out of date.
This prototype provides a graphical user interface, using WebJive, that runs in Docker containers defined in the configuration files `tangogql.yml`, `traefik.yml`, and `webjive.yml`. To use, start the Docker containers, then navigate to `localhost:22484/testdb`. The following credentials can be used:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can be seen and modified, and device commands can be sent, by creating and saving a new dashboard.



## License

See the `LICENSE` file for details.
