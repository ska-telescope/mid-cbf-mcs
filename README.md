Documentation on the Developer's portal:
[![ReadTheDoc](https://developer.skatelescope.org/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skatelescope.org/projects/mid-cbf-mcs/en/latest/?badge=latest)

# TABLE OF CONTENTS (TODO)
* 1 - [Introduction](#description)
* 2 - [Getting started](#getting-started)
  * 2.0 - [Harware and OS requirements (TODO)](#hw_req)
  * 2.1 - [Install a Virtual Machine](#install_VM)
  * 2.2 - [Install Ubuntu](#install_Ubuntu)
  * 2.3 - [Create a Development Environment](#setup_Tango)
  * 2.4 - [Setup Kubernetes](#setup_Kubernetes)
  * 2.5 - [Setup the Mid.CBF MCS Software](#setup_MCS)
* 3 - [Running the Mid.CBF MCS](#run_MCS)
  * 3.1 - [Running Using Kubernetes](#run_Kubernetes)
  * 3.2 - [Running Using Docker-Compose (deprecated)](#run_Docker_Compose)
* 4 - [WebJIVE GUI](#jive-gui)
* 5 - [Development resources](#dev-resources)
  * 5.1 - [Other resources](#other-resources)
  * 5.2 - [Useful commands](#commands)
* 6 - [Release](#release)
* 7 - [License](#license)

# 1 Introduction

The Mid CBF MCS prototype implements at the moment these TANGO device classes:

* `CbfController`: Based on the `SKAMaster` class. It represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a set of housekeeping commands.
* `CbfSubarray`: Based on the `SKASubarray` class. It implements commands needed for scan configuration.

* `Vcc` and `Fsp`: Based on the `SKACapability` class. These implement commands and attributes needed for scan configuration.
* `Vcc` and `Fsp` Capabilities: Based on the `SKACapability` class. These implement state machines to enable/disable certain VCC and FSP functionality for a scan.
    * `VccBand1And2`, `VccBand3`, `VccBand4`, and `VccBand5` specify the operative frequency band of a VCC.
    * `VccSearchWindow` defines a search window for a VCC.
    * `FspCorr`, `FspPss`, `FspPst`, and `FspVlbi` specify the function mode of an FSP.
    * `FspCorrSubarray`: Based on the `SKASubarray` class. It implements commands and attributes needed for scan configuration.
* `TmCspSubarrayLeafNodeTest`: Based on the `SKABaseDevice` class. It simulates a TM CSP Subarray Leaf Node, providing regular updates to parameters during scans using a publish-subscribe mechanism.

To cut down on the number of TANGO device servers, some multi-class servers are implemented to run devices of different classes:

* `CbfSubarray`: Runs a single instance of `CbfSubarray`
* `VccMulti`: Runs a single instance of `Vcc`, one instance each of the VCC frequency band capabilities, and two instances of ``VccSearchWindow``.
* `FspMulti`: Runs a single instance of `Fsp`, one instance each of the FSP function mode capabilities, and 4 instances of `FspCorrSubarray`.

At the moment, the device servers implemented are:

* 1 instance of `CbfController`.
* 2 instance of `CbfSubarray`.
* 4 instances of `FspMulti`.
* 4 instances of `VccMulti`.
* 1 instance of `TmCspSubarrayLeafNodeTest`.

# 2 Getting started

The following instruction follow the instructions on the SKA developer’s portal: 

* https://developer.skatelescope.org/en/latest/getting-started/devenv-setup/tango-devenv-setup.html

and

* https://developer.skatelescope.org/en/latest/tools/dev-faq.html


*Note*: For the entire skatelescope.org developer's documentation in PDF format see: 

https://developer.skatelescope.org/_/downloads/en/latest/pdf/

## 2.0 Hardware and OS requirements (TODO)

## 2.1 Install a Virtual Machine

1.  Download Virtualbox from: https://www.virtualbox.org/wiki/Downloads

2.  Install Virtualbox

## 2.2 Install Ubuntu

Download an image of ubuntu 18.04, for example like the following one:

https://sourceforge.net/projects/osboxes/files/v/vb/55-U-u/18.04/18.04.2/18042.64.7z/download

Steps:

1.  Open up the file downloaded from sourceforge for the ubuntu image with 7-zip and extract the “Ubuntu 18.04.2 (64bit).vdi” file into a known directory

2.  Open up the virtual box software and click “new” and run through the setup process, on the Hard Disk option screen choose “use and existing virtual hard disk file” and then choose the VDI file that you extracted in step two.

3.  Run the OS in virtualbox and login to the ubuntu OS. The login screen should show the account “osboxes.org” it will ask for a password, this is a default account the virtual machine creates for you and the password is **“osboxes.org”** (you can change the name and password in account settings once you are logged in”)

*Note* : If you set your own password for the virtual machine, change "ansible_become_pass=osboxes.org" to "ansible_become_pass=your_own_password"

## 2.3 Create a Development Environment 

Setting up the Development environment, including Tango environment,  is performed using the ansible playbook script. Follow the commands in the yellow box under the 'Creating a Development Environment' section of the https://developer.skatelescope.org/en/latest/getting-started/devenv-setup/tango-devenv-setup.html web page.

See that page for a list of the applications installed in this way.

### Notes and Troubleshooting

*Note 1*: If you already have an older installation don't forget to first update your local version of the ansible-playbooks repo (pull, checkout or delete and clone again), before running the ansible-playbooks command.

*Note 2*: You may need to precede the ``ansible-playbook`` command (from the commands sequence at the link above) by ``sudo``.

*Note 3*:  Depending on your system, the ``ansible-playbook`` command may take more than one hour to complete.

*Note 4*: If you encounter Python installation problem with the ansible command, try to explicitly specify the python version in the ansible command, for example:
```
ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org" -e ansible_python_interpreter=/usr/bin/python3
```

*Note 5*: If you experience other issues with the script ask questions in the #team-system-support slack channel.

## 2.4 Setup Kubernetes

For installing Kubernetes, Minikube and Helm, follow the instructions at ```https://developer.skatelescope.org/en/latest/tools/dev-faq.html```.

Follow the instruction in the README of ``ska-cicd-deploy-minikube``

## 2.5 Setup the Mid.CBF MCS Software

The following projects are required:
* ska-mid-cbf-mcs
* ska-tango-base

To get a local copy of the mid-cbf-mcs project:
```
git clone https://gitlab.com/ska-telescope/ska-mid-cbf-mcs.git
```

To install ska-tang-base (as a Python package)  follow the 'Installation steps' of the README at: ```https://gitlab.com/ska-telescope/ska-tango-base```


Note that SKA Tango Classes are needed for example when using Pogo to automatically generate Python TANGO code. Pogo will ask for the Base class pogo (.xmi) files. 
Navigate to the Base class folder (typically when you run "pogo xxx", and the base class file is not configured). TODO

# 3 Running the Mid.CBF MCS

The ska-mid-cbf-mcs Tango device servers are started and run via Kubernetes. 

Make sure Kubernetes, Helm and Minikube have been installed (and verified) as described in the 'Setup Kubernetes' section.

1 - You may need to change permission to the .minikube and .kube files in your home directory:
```
sudo chown -R <user_name>:<user_name> ~/.minikube/
sudo chown -R m <user_name>:<user_name> ~/.kube/
```

2 - From the root of the project, run:

```
make build 
make install-chart
make watch
make test
```
Note: ``make build`` is required only if a local image needs to be built, for example every time the SW has been updated )
The last command will list all pods in 'real time'; wait until all pods have status 'Completed' or 'Running'.

### Configuring scan (TODO)

To configure scan with JIVE, the input file needs “\” before each quotation mark. Normal JSON file wouldn’t work.
To solve this problem, there are 2 options:
1. Use a script to generate this specific input as follows:
Copy your JSON file into the tangods/CbfSubarray/JIVEconfigscan/scanconfig.json file; then run:

```Python generateJIVE.py```

2. Use the sendConfig device to trigger configure scan with the subarray. Copy the configuration JSON file into tangods/CbfSubarray/sendConfig/config.JSON.

## 4 WebJive GUI (TODO)

Note: WebJive GUI is currently out of date. TODO
This prototype provides a graphical user interface, using WebJive, that runs in Docker containers defined in the configuration files `tangogql.yml`, `traefik.yml`, and `webjive.yml`. To use, start the Docker containers, then navigate to `localhost:22484/testdb`. The following credentials can be used:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can be seen and modified, and device commands can be sent, by creating and saving a new dashboard.

## 5 Development resources

### 5.1 Other resources

See more instructions and examples in the `ska-tango-example` repository

### 5.2 Useful commands

For Kubernetes basic commands see: https://kubernetes.io/docs/reference/kubectl/cheatsheet/

To display the Kubernetes nodes and images that have been started up:

```
kubectl get all -n mid-cbf
```

To list the running containers issue:
```
docker ps
```
To list all created containers (not only running):
```
docker ps -a
``` 
To list all created containers but less verbose, run for example:
```
docker ps -a --format "table {{.ID}}\t{{.Status}}\t{{.Names}}"
``` 
These commands should list the following running containers:

* `midcbf-cbfcontroller`: The `CbfController` TANGO device server.
* `midcbf-cbfsubarrayxx`ranges from `01` to `02` The 2 instances of the `CbfSubarray` TANGO device server.
* `midcbf-fspxx`: `xx` ranges from `01` to `04`. The 4 instances of the `FspMulti` TANGO device servers.
* `midcbf-vccxx`: `x` ranges from `01` to `04`. The 4 instances of the `VccMulti` TANGO device servers.
* `midcbf-tmcspsubarrayleafnodetest`: The `TmCspSubarrayLeafNodeTest` TANGO device server.
* `midcbf-rsyslog`: The rsyslog container for the TANGO devices.
* `midcbf-databaseds`: The TANGO DB device server.
* `midcbf-tangodb`: The MySQL database with the TANGO database tables.
* etc.

## 6 Release

For a new release (i.e. prior to merging a branch into master) update the following fields by incrementing the version/release/tag number to conform to the semanthic versioning convention:
* `.release` file: update the `version`, `tag` and `release` fields.
* `.values.yaml` fie: update the `tag` field inder `midcbf: image:`
* `charts/mid-cbf/Chart.yaml` file: update `version` and `appVersion`
* `charts/mid-cbf-umbrella/Chart.yaml` file: update `version`, `appVersion` and `version` of the `mid-cbf` entry.

Note: `appVersion` represents the version of the application running, so it correspons to the ska-mid-cbf-mcs docker image version.
## 7 License

See the `LICENSE` file for details.
