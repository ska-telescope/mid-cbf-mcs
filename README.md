# Mid.CBF MCS

Documentation on the Developer's portal:
[![ReadTheDoc](https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)

# TABLE OF CONTENTS
* 1.0 - [Introduction](#description)
* 2.0 - [Getting started](#getting-started)
  * 2.1 - [Hardware and OS requirements](#hw_req)
  * 2.2 - [Install a virtual vachine](#install_VM)
  * 2.3 - [Install Ubuntu](#install_Ubuntu)
  * 2.4 - [Set up development environment](#setup_Tango)
  * 2.5 - [Setup Kubernetes](#setup_Kubernetes)
  * 2.6 - [Setup the Mid.CBF MCS Software](#setup_MCS)
* 3.0 - [Running the Mid.CBF MCS](#run_MCS)
* 4.0 - [WebJIVE GUI](#jive-gui)
* 5.0 - [Development resources](#dev-resources)
  * 5.1 - [Other resources](#other-resources)
  * 5.2 - [Useful commands](#commands)
* 6.0 - [Release](#release)
* 7.0 - [License](#license)

# 1.0 - Introduction

The Mid CBF MCS prototype implements at the moment these TANGO device classes:

* `CbfController`: Based on the `SKAMaster` class. It represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a set of housekeeping commands.
* `CbfSubarray`: Based on the `SKASubarray` class. It implements commands needed for scan configuration.

* `Vcc` and `Fsp`: Based on the `SKACapability` and `CspSubelementObsDevice` classes, respectfully. These implement commands and attributes needed for scan configuration.
* `Vcc` and `Fsp` Capabilities: Based on the `SKACapability` class. These implement state machines to enable/disable certain VCC and FSP functionality for a scan.
    * `VccBand1And2`, `VccBand3`, `VccBand4`, and `VccBand5` specify the operative frequency band of a VCC.
    * `VccSearchWindow` defines a search window for a VCC.
    * `FspCorr`, `FspPss`, `FspPst`, and `FspVlbi` specify the function mode of an FSP.
    * `FspCorrSubarray`, `FspPssSubarray` and `FspPssSubarray`: Based on the `SKASubarray` class. It implements commands and attributes needed for scan configuration.
* `TmCspSubarrayLeafNodeTest`: Based on the `SKABaseDevice` class. It simulates a TM CSP Subarray Leaf Node, providing regular updates to parameters during scans using a publish-subscribe mechanism.

To cut down on the number of TANGO device servers, some multi-class servers are implemented to run devices of different classes:

* `VccMulti`: Runs a single instance of `Vcc`, one instance each of the VCC frequency band capabilities, and two instances of ``VccSearchWindow``.
* `FspMulti`: Runs a single instance of `Fsp`, one instance each of the FSP function mode capabilities, and 4 instances each of `FspCorrSubarray`, `FspPssSubarray` and `FspPssSubarray`.

At the moment, the device servers implemented are:

* 1 instance of `CbfController`.
* 3 instance of `CbfSubarray`.
* 4 instances of `FspMulti`.
* 4 instances of `VccMulti`.
* 2 instance of `TmCspSubarrayLeafNodeTest`.

# 2.0 - Getting started

This section follows the instructions on the SKA developer’s portal: 

* https://developer.skao.int/en/latest/getting-started/devenv-setup.html
* https://developer.skao.int/en/latest/tools/dev-faq.html

## 2.1 - Hardware and OS requirements

The following settings are needed for the virtual machine, running on a Windows 10 host:
* 4 CPUs
* 8 GB RAM
* ~40 GB storage

## 2.2 - Install a virtual machine

Download and install VirtualBox from: https://www.virtualbox.org/wiki/Downloads

## 2.3 - Install Ubuntu

Download an image of Ubuntu 18.04 like the following one:

https://sourceforge.net/projects/osboxes/files/v/vb/55-U-u/18.04/18.04.2/18042.64.7z/download

Steps:

1.  Open up the file downloaded from SourceForge for the Ubuntu image with 7-Zip and extract the “Ubuntu 18.04.2 (64bit).vdi” file into a known directory.

2.  Open up the VirtualBox software and click “new” and run through the setup process, on the Hard Disk option screen choose “use and existing virtual hard disk file” and then choose the VDI file that you extracted in step two.

3.  Run the OS in VirtualBox and login to the Ubuntu OS. The login screen should show the account “osboxes.org” it will ask for a password, this is a default account the virtual machine creates for you and the password is **“osboxes.org”** (you can change the name and password in account settings once you are logged in”).

*Note* : If you set your own password for the virtual machine, change "ansible_become_pass=osboxes.org" to "ansible_become_pass=your_own_password"

## 2.4 - Set up development environment 

Setting up the Development environment, including Tango environment,  is performed using the ansible playbook script. Follow the commands in the yellow box under the 'Creating a Development Environment' section of the https://developer.skatelescope.org/en/latest/getting-started/devenv-setup/tango-devenv-setup.html web page.

See that page for a list of the applications installed in this way.

### Notes and troubleshooting

*Note 1*: If you already have an older installation don't forget to first update your local version of the ansible-playbooks repo (pull, checkout or delete and clone again), before running the ansible-playbooks command.

*Note 2*: You may need to precede the ``ansible-playbook`` command (from the commands sequence at the link above) by ``sudo``.

*Note 3*:  Depending on your system, the ``ansible-playbook`` command may take more than one hour to complete.

*Note 4*: If you encounter Python installation problem with the ansible command, try to explicitly specify the python version in the ansible command, for example:
```
ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org" -e ansible_python_interpreter=/usr/bin/python3
```

*Note 5*: If you experience other issues with the script ask questions in the #team-system-support slack channel.

## 2.5 Set up Kubernetes

For installing Kubernetes, Minikube and Helm, follow the instructions at ```https://developer.skatelescope.org/en/latest/tools/dev-faq.html```.

### Individual installation instructions:
* [Docker Engine](https://docs.docker.com/engine/install/ubuntu/)
* [minikube](https://minikube.sigs.k8s.io/docs/start/)
  * Follow the instructions in the README of `https://gitlab.com/ska-telescope/ska-cicd-deploy-minikube`
* [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
* [Helm](https://helm.sh/docs/intro/install/)


## 2.6 Setup the Mid.CBF MCS Software

The following projects are required:
* ska-mid-cbf-mcs
* ska-tango-base
* ska-cicd-deploy-minikube

To get a local copy of the ska-mid-cbf-mcs project:
```
git clone https://gitlab.com/ska-telescope/ska-mid-cbf-mcs.git
```

To install ska-tango-base (as a Python package)  follow the 'Installation steps' of the README at: `https://gitlab.com/ska-telescope/ska-tango-base`


*Note*:SKA Tango base classes are needed when using Pogo to automatically generate Python TANGO code. Pogo will ask for the Base class pogo (.xmi) files, which are located in the ska-tango-base folder.

# 3.0 Running the Mid.CBF MCS

The ska-mid-cbf-mcs Tango device servers are started and run via Kubernetes. 

Make sure Kubernetes, Helm and Minikube have been installed (and verified) as described in the 'Set up Kubernetes' section.

*Note*: You may need to change permission to the .minikube and .kube files in your home directory:
```
sudo chown -R <user_name>:<user_name> ~/.minikube/
sudo chown -R m <user_name>:<user_name> ~/.kube/
```


### 1.  Make sure minikube is up and running; use ```minikube start``` and ```minikube stop``` to start and stop the local kubernetes node.

### 2.  From the root of the project, run `make build` to build the application image.

`make build` is required only if a local image needs to be built, for example every time the SW has been updated. For development, in order to get local changes to build, run `eval $(minikube docker-env)` before `make build`; see https://stackoverflow.com/questions/52310599/what-does-minikube-docker-env-mean

### 3.  Install the umbrella chart.
```
make install-chart
make watch
```
*Note*: `make watch` will list all of the pods' status in 'real time'; wait until all pods have status 'Completed' or 'Running'.

### 4.  (optional) Create python virtual environment to isolate project specific packages from your host environment: in the project root run `virtualenv venv` to create then `source venv/bin/activate` to run (to exit run `deactivate`) 

### 5.  Run `make requirements` for linting and testing.

### 6.  To tear down the deployment, run ```make uninstall-chart```

# 4.0 WebJive GUI

This prototype provides a graphical user interface, using WebJive; to use, deploy with ```make install-chart-with-taranta```, then navigate to `integration.engageska-portugal.pt` in a browser. The following credentials can be used:

* Username: `CIPA`
* Password: `CIPA_SKA`

The device tree can be viewed and explored. In addition, device attributes can be seen and modified, and device commands can be sent, by creating and saving a new dashboard.

# 5.0 Development resources

### 5.1 Other resources

See more tango device guidelines and examples in the `ska-tango-examples` repository

### 5.2 Useful commands

For Kubernetes basic kubectl commands see: https://kubernetes.io/docs/reference/kubectl/cheatsheet/

To display all components of the Kubernetes system:

```
kubectl get all -n ska-mid-cbf
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

# 6.0 Release

For a new release (i.e. prior to merging a branch into master) update the following fields by incrementing version/release/tag numbers to conform to the semantic versioning convention:
* `.release`: `release=` and `tag=`
* `src/ska_mid_cbf_mcs/release.py`: `version = `
* `charts/ska-mid-cbf/Chart.yaml`: `version:` and `appVersion:`
* `charts/ska-mid-cbf/values.yaml`: `tag:` field under `midcbf: image:`
* `charts/ska-mid-cbf-tmleafnode/Chart.yaml`: `version:` and `appVersion:`
* `charts/ska-mid-cbf-tmleafnode/values.yaml`: `tag:` field under `midcbf: image:`
* `charts/mid-cbf-umbrella/Chart.yaml`: 
  * `version:`, `appVersion:`
  * `version:` under `ska-mid-cbf` and `ska-mid-cbf-tmleafnode`.

*Note*: `appVersion` represents the version of the application running, so it corresponds to the ska-mid-cbf-mcs docker image version.

Once a new release has been merged into master, create a new tag on GitLab and run the manual "publish-chart" stage of the tag pipeline to publish the Helm charts.

# 7.0 License

See the `LICENSE` file for details.
