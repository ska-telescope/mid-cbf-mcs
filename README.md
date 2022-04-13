# Mid.CBF MCS

Documentation on the Developer's portal:
[![ReadTheDocs](https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)](https://developer.skao.int/projects/ska-mid-cbf-mcs/en/latest/?badge=latest)

Code repository: [ska-mid-cbf-mcs](https://gitlab.com/ska-telescope/ska-mid-cbf-mcs)

# Table Of Contents
* [Introduction](#introduction)
* [Getting started](#getting-started)
  * [Hardware and OS requirements](#hardware-and-os-requirements)
  * [Install a virtual vachine](#install-a-virtual-machine)
  * [Install Ubuntu](#install-ubuntu)
  * [Set up development environment](#set-up-development-environment) 
  * [Set up the Mid CBF MCS Software](#set-up-the-mid-cbf-mcs-software)
  * [Set up Kubernetes](#set-up-kubernetes)
* [Running the Mid CBF MCS](#running-the-mid-cbf-mcs)
* [Jive and Taranta](#jive-and-taranta)
* [Documentation](#documentation)
* [Releasing](#releasing)
* [Development resources](#development-resources)
  * [Other resources](#other-resources)
  * [Useful commands](#commands)
* [License](#license)

# Introduction

The Mid CBF MCS prototype implements at the moment these TANGO device classes:

* `CbfController`: Based on the `SKAController` class. It represents a primary point 
of contact for CBF Monitor and Control. It implements CBF state and mode 
indicators 
and a set of housekeeping commands.
* `CbfSubarray`: Based on the `SKASubarray` class. It implements commands needed 
for scan configuration.

* `Vcc` and `Fsp`: Based on the `SKACapability` and `CspSubelementObsDevice` 
classes, respectfully. These implement commands and attributes needed for scan 
configuration.
* `Vcc` and `Fsp` Capabilities: Based on the `SKACapability` class. These 
implement state machines to enable/disable certain VCC and FSP functionality for 
a scan.
    * `VccBand1And2`, `VccBand3`, `VccBand4`, and `VccBand5` specify the 
    operative frequency band of a VCC.
    * `VccSearchWindow` defines a search window for a VCC.
    * `FspCorr`, `FspPss`, `FspPst`, and `FspVlbi` specify the function mode of 
    an FSP.
    * `FspCorrSubarray`, `FspPssSubarray` and `FspPssSubarray`: Based on the 
    `SKASubarray` class. It implements commands and attributes needed for scan 
    configuration.
* `TmCspSubarrayLeafNodeTest`: Based on the `SKABaseDevice` class. It simulates 
a TM CSP Subarray Leaf Node, providing regular updates to parameters during 
scans using a publish-subscribe mechanism.

To cut down on the number of TANGO device servers, some multi-class servers are 
implemented to run devices of different classes:

* `VccMulti`: Runs a single instance of `Vcc`, one instance each of the VCC 
frequency band capabilities, and two instances of ``VccSearchWindow``.
* `FspMulti`: Runs a single instance of `Fsp`, one instance each of the FSP 
function mode capabilities, and 4 instances each of `FspCorrSubarray`, 
`FspPssSubarray` and `FspPssSubarray`.

At the moment, the device servers implemented are:

* 1 instance of `CbfController`.
* 3 instance of `CbfSubarray`.
* 4 instances of `FspMulti`.
* 4 instances of `VccMulti`.
* 2 instances of `TmCspSubarrayLeafNodeTest`.

# Getting started

This section follows the instructions on the SKA developer’s portal: 

* https://developer.skao.int/en/latest/getting-started/devenv-setup.html
* https://developer.skao.int/en/latest/tools/dev-faq.html

## Hardware and OS requirements

The following settings are needed for the virtual machine, running on a Windows 
10 host:
* 4 CPUs
* 8 GB RAM (ideally more, maximum that VirtualBox recommends)
* ~40 GB storage

## Install a virtual machine

Download and install VirtualBox and the extension pack from: 
https://www.virtualbox.org/wiki/Downloads

## Install Ubuntu

Download an image of Ubuntu 18.04 like the following one:

https://sourceforge.net/projects/osboxes/files/v/vb/55-U-u/18.04/18.04.2/18042.64.7z/download

Steps:

1.  Open up the file downloaded from SourceForge for the Ubuntu image with 7-Zip 
and extract the “Ubuntu 18.04.2 (64bit).vdi” file into a known directory.

2.  Open up the VirtualBox software and click “new” and run through the setup 
process, on the Hard Disk option screen choose “use and existing virtual hard 
disk file” and then choose the VDI file that you extracted in step two.

3.  Run the OS in VirtualBox and login to the Ubuntu OS. The login screen should 
show the account `osboxes.org`; this is a default account the virtual machine 
creates for you and the password is **`osboxes.org`** (you can change the name 
and password in account settings once you are logged in”).

*Note* : If you set your own password for the virtual machine, change 
"ansible_become_pass=osboxes.org" to "ansible_become_pass=your_own_password"

## Set up development environment 

### DEPRECATION NOTICE
`ansible-playbooks` repository no longer supported, however it is still useful 
to set up a new development environment.

Setting up the Development environment, including Tango environment,  is 
performed using the ansible playbook script. Follow the commands in the yellow 
box under the 'Creating a Development Environment' section of the 
https://developer.skatelescope.org/en/latest/getting-started/devenv-setup/tango-devenv-setup.html 
web page.

```
sudo apt -y install git
git clone https://gitlab.com/ska-telescope/ansible-playbooks
cd ansible-playbooks
sudo apt-add-repository --yes --update ppa:ansible/ansible && \
    sudo apt -y install ansible
ansible-playbook -i hosts deploy_tangoenv.yml \
    --extra-vars "ansible_become_pass=osboxes.org" \
    -e ansible_python_interpreter=/usr/bin/python
sudo reboot
```

See that page for a list of the applications installed in this way.

### Notes and troubleshooting

*Note 1*: If you already have an older installation don't forget to first update 
your local version of the ansible-playbooks repo (pull, checkout or delete and 
clone again), before running the ansible-playbooks command.

*Note 2*: You may need to precede the ``ansible-playbook`` command (from the 
commands sequence at the link above) by ``sudo``.

*Note 3*:  Depending on your system, the ``ansible-playbook`` command may take 
more than one hour to complete.

*Note 4*: If you encounter Python installation problem with the ansible command, 
try to explicitly specify the python version in the ansible command, for example:
```
ansible-playbook -i hosts deploy_tangoenv.yml --extra-vars "ansible_become_pass=osboxes.org" -e ansible_python_interpreter=/usr/bin/python3
```

*Note 5*: If you experience other issues with the script ask questions in the 
[#team-system-support](https://skao.slack.com/archives/CEMF9HXUZ) slack channel.

## Set up the Mid CBF MCS Software

The basic requirements are:
* Python 3.5
* pip

The following projects are required:
* ska-mid-cbf-mcs
* ska-tango-base

To get a local copy of the ska-mid-cbf-mcs project:
```
git clone https://gitlab.com/ska-telescope/ska-mid-cbf-mcs.git  # clone the MCS 
repository locally
```

To install ska-tango-base (as a Python package), follow the 'Installation steps' 
of the README at https://gitlab.com/ska-telescope/ska-tango-base

*Note*:SKA Tango base classes are needed when using Pogo to automatically 
generate Python TANGO code. Pogo will ask for the Base class pogo (.xmi) files, 
which are located in the ska-tango-base folder.

## Set up Kubernetes

For installing Kubernetes, Minikube and Helm, follow the instructions at 
```https://developer.skatelescope.org/en/latest/tools/dev-faq.html```.

### Individual installation instructions
* [Docker Engine](https://docs.docker.com/engine/install/ubuntu/)
* [minikube](https://minikube.sigs.k8s.io/docs/start/), 
[kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) 
and [Helm](https://helm.sh/docs/intro/install/)
  * Clone the `https://gitlab.com/ska-telescope/sdi/ska-cicd-deploy-minikube` 
  project and follow the README instructions to install and configure minikube, 
  kubectl and Helm correctly.

# Running the Mid CBF MCS

The ska-mid-cbf-mcs Tango device servers are started and run via Kubernetes. 

Make sure Kubernetes/minikube and Helm have been installed (and verified) as 
described in the 'Set up Kubernetes' section.

*Note*: You may need to change permission to the .minikube and .kube files in 
your home directory:
```
sudo chown -R <user_name>:<user_name> ~/.minikube/
sudo chown -R <user_name>:<user_name> ~/.kube/
```

#### 1.  Make sure minikube is up and running
The following commands use the default minikube profile. If you are running the MCS on the Dell server you will need to set up your own minikube profile. A new minikube profile is needed for a new cluster, so creating minikube profiles ensures two users on the Dell server do not work on the same cluster at the same time. To view the modifications needed to run the following commands on a new minikube profile see Minikube Profiles

```
minikube start    # start minikube (local kubernetes node)
minikube status   # check current status of minikube
```

#### 2.  From the root of the project, build the application image.
```
cd ska-mid-cbf-mcs
eval $(minikube docker-env)  # if building from local source and not artefact repository
make build
```

`make build` is required only if a local image needs to be built, for example 
every time the SW has been updated. 
[For development, in order to get local changes to build, run `eval $(minikube docker-env)` before `make build`](https://v1-18.docs.kubernetes.io/docs/setup/learning-environment/minikube/#use-local-images-by-re-using-the-docker-daemon)

#### 3.  Install the umbrella chart.
```
make install-chart        # deploy from Helm charts
make install-chart-only   # deploy from Helm charts without updating dependencies
```
*Note*: `make watch` will list all of the pods' status in every 2 seconds using 
kubectl; `make wait` will wait until all jobs are 'Completed' and pods are 
'Running'.

#### 4.  (Optional) Create python virtual environment to isolate project specific dependencies from your host environment.
```
virtualenv venv           # create python virtualenv 'venv'
source venv/bin/activate  # activate venv
```

#### 5.  Install linting and testing requirements.
```
make requirements
```

#### 6.  Install the MCS package in editable mode.
```
pip install -e .
```

#### 7.  Run a test.
```
make test       # functional tests, creates a running deployment
make test-only  # functional tests with an already running deployment
make unit-test  # unit tests, deployment does not need to be running
```
*Note*: add `-k` pytest flags in `setup.cfg` in the project root to limit which 
tests are run

#### 8.  Tear down the deployment.
```
make uninstall-chart                  # uninstall deployment from Helm charts
deactivate                            # if in active virtualenv
eval $(minikube docker-env --unset)   # if docker-env variables were set previously
minikube stop                         # stop minikube
```

# Minikube Profiles

### Create a minikube profile
```
minikube start -p <profile_name>
```

### Check the status of the cluster created for your minikube profile
```
minikube status -p <profile_name>
```

### Switch to a pre-existing minikube profile
```
minikube profile <profile_name>
```

### Check which minikube profile you are on
```
minikube profile
```

### List all minikube profiles
```
minikube profile list
```

### Set and unset docker-env variables
```
eval $(minikube docker-env -p <profile_name>) 
eval $(minikube docker-env --unset -p <profile_name>) 
```

### Verify the kubectl context matches the minikube profile name
In order to use kubectl to get pod information via the command line, the kubectl 'conext' should match the minikube profile. To verify this the output of `minikube profile` should match the output of `kubectl config current-context`
```
kubectl config current-context
```

### Delete a minikube profile
```
minikube delete -p <profile_name>
```



# Jive and Taranta

## Jive
Run `make jive` with the deployment active to get a command useful for configuring 
local Jive; this command sets the TANGO_HOST environment variable equal to 
```<minikube-IP-address>:<database-pod-TCP-port>```.
```
make jive   # copy and paste the output
jive&       # run Jive
```

## Taranta
This prototype provides a graphical user interface using Taranta (previously known as WebJive); to set it up:
* Add the following line to `/etc/hosts`:
    ```
    192.168.49.2  taranta
    ```
    *Note*: 192.168.49.2 is the minikube IP address, obtainable with the command `minikube ip`
* Deploy with `make install-chart-with-taranta`
* Navigate to `taranta/ska-mid-cbf/taranta/devices` in a browser (works best with Google Chrome).

The following credentials can be used to operate the system:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can 
be seen and modified, and device commands can be sent, by creating and saving a 
new dashboard.

# Documentation
To re-generate the documentation locally prior to checking in updates to Git:
```bash
make documentation
```
To see the generated documentation, open `/ska-mid-cbf-mcs/docs/build/html/index.html` in a browser -- e.g.,
```
firefox docs/build/html/index.html &
```

# Releasing

For a new release (i.e. prior to merging a branch into main) update the 
following files by incrementing version/release/tag number fields to conform to 
the semantic versioning convention:
* `.release`: `release=` and `tag=`
* `src/ska_mid_cbf_mcs/release.py`: `version = `
* `charts/ska-mid-cbf/Chart.yaml`: `version:` and `appVersion:`
* `charts/ska-mid-cbf/values.yaml`: `midcbf:image:tag:`
* `charts/ska-mid-cbf-tmleafnode/Chart.yaml`: `version:` and `appVersion:`
* `charts/ska-mid-cbf-tmleafnode/values.yaml`: `midcbf:image:tag:`
* `charts/mid-cbf-umbrella/Chart.yaml`: 
  * `version:` and `appVersion:`
  * `version:` under `ska-mid-cbf` and `ska-mid-cbf-tmleafnode`

*Note*: `appVersion` represents the version of the application running, so it 
corresponds to the ska-mid-cbf-mcs docker image version.

Once a new release has been merged into main, create a new tag on GitLab and 
run the manual "publish-chart" stage of the tag pipeline to publish the 
Helm charts.

# Development resources

### Other resources

See more tango device guidelines and examples in the `ska-tango-examples` 
repository

### Useful commands

#### Kubernetes
For Kubernetes basic kubectl commands see: 
https://kubernetes.io/docs/reference/kubectl/cheatsheet/

To display components of the MCS Kubernetes system:

```
kubectl get all -n ska-mid-cbf
kubectl describe <component-name> -n ska-mid-cbf  # info on a particular component
```
This should list the following running pods:

* `cbfcontroller-controller-0 `: The `CbfController` TANGO device server.
* `cbfsubarrayxx-cbf-subarray-xx-0`: `xx` ranges from `01` to `03`. 
The 3 instances of the `CbfSubarray` TANGO device server.
* `fspxx-fsp-xx-0`: `xx` ranges from `01` to `04`. 
The 4 instances of the `FspMulti` TANGO device servers.
* `vccxxx-vcc-xxx-0`: `xxx` ranges from `001` to `004`. 
The 4 instances of the `VccMulti` TANGO device servers.
* `tmcspsubarrayleafnodetestx-tmx-0`: `x` ranges from `1` to `2`. 
The 2 instances of the `TmCspSubarrayLeafNodeTest` TANGO device servers.
* `tango-host-databaseds-from-makefile-test-0`: The TANGO DB device server.
* etc.

#### Docker
Set up Docker run without `sudo`:
```
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
```
System info and cleanup:
```
docker system info
docker system prune
docker images
docker image rm <image-ID(s)>
docker volume ls
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

# License

See the `LICENSE` file for details.
