# Developer Setup

This section follows the instructions on the SKA developer’s portal: 

* [Dev Environment Setup](https://developer.skao.int/en/latest/getting-started/devenv-setup.html)
* [Dev FAQs](https://developer.skao.int/en/latest/tools/dev-faq.html)

# Git Repository

The MCS Git Repository is available at the following page:
[https://gitlab.com/ska-telescope/ska-mid-cbf-mcs](https://gitlab.com/ska-telescope/ska-mid-cbf-mcs)

The README on the repository will guide users through cloning and initializing the repository.

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

## 1.  Make sure minikube is up and running
The following commands use the default minikube profile. If you are running the MCS on the Dell server you will need to set up your own minikube profile. A new minikube profile is needed for a new cluster, so creating minikube profiles ensures two users on the Dell server do not work on the same cluster at the same time. To view the modifications needed to run the following commands on a new minikube profile see Minikube Profiles

```
minikube start    # start minikube (local kubernetes node)
minikube status   # check current status of minikube
```

The `minikube status` output should be:
```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

If restarting a stopped minikube; from local `ska-cicd-deploy-minikube` repository 
run `make minikube-metallb-config` to reapply metallb configMap to determine pod
LoadBalancer service external IP addresses.

## 2.  From the root of the project, build the application image.
```
cd ska-mid-cbf-mcs
eval $(minikube docker-env)   # to use the minikube's docker environment 
make oci-image-build          # if building from local source and not artefact repository
```

`make oci-image-build` is required only if a local image needs to be built, for example 
every time the SW has been updated. 
[For development, in order to get local changes to build, run `eval $(minikube docker-env)` before `make build`](https://v1-18.docs.kubernetes.io/docs/setup/learning-environment/minikube/#use-local-images-by-re-using-the-docker-daemon)

*Note*: To check if you are within the minikube's docker environment, use the
`minikube status` command. It will indicate `docker-env: in use` if in use as
follows:
```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
docker-env: in-use
```

## 3.  Install the umbrella chart.
```
make k8s-install-chart        # deploy from Helm charts
make k8s-install-chart-only   # deploy from Helm charts without updating dependencies
```
*Note*: `make k8s-watch` will list all of the pods' status in every 2 seconds using 
kubectl; `make k8s-wait` will wait until all jobs are 'Completed' and pods are 
'Running'.

## 4.  (Optional) Create python virtual environment to isolate project specific dependencies from your host environment.
```
virtualenv venv           # create python virtualenv 'venv'
source venv/bin/activate  # activate venv
```

## 5.  Install linting and testing requirements.
```
make requirements
```

## 6.  Install the MCS package in editable mode.
```
pip install -e .
```

## 7.  Run a test.
```
make k8s-test  # functional tests with an already running deployment
make python-test  # unit tests, deployment does not need to be running
```
*Note*: add `-k` pytest flags in `setup.cfg` in the project root to limit which 
tests are run

## 8.  Tear down the deployment.
```
make k8s-uninstall-chart              # uninstall deployment from Helm charts
deactivate                            # if in active virtualenv
eval $(minikube docker-env --unset)   # if docker-env variables were set previously
minikube stop                         # stop minikube
```

# Useful Minikube Commands

## Create a minikube 
```
minikube start 
```

## Check the status of the cluster created for your minikube 
```
minikube status 
```

## Fixing a Misconfigured Kubeconfig

If the kubeconfig is pointing to a stale minikube and is showing as `Misconfigured` 
when checking the `minikube status`, or if the minikube's IP or port has changed, 
update the context as follows:
```
minikube update-context
```

## Delete a minikube profile
```
minikube delete
```

## Set and unset docker-env variables
```
eval $(minikube docker-env)
eval $(minikube docker-env --unset)
```

# Taranta

This provides a graphical user interface using Taranta (previously known as WebJive); to set it up:
* Add the following line to `/etc/hosts`:
    ```
    192.168.49.2  taranta
    ```
    *Note*: 192.168.49.2 is the minikube IP address, obtainable with the command `minikube ip`
* Navigate to `taranta/ska-mid-cbf/taranta/devices` in a browser (works best with Google Chrome).

The following credentials can be used to operate the system:

* Username: `user1`
* Password: `abc123`

The device tree can be viewed and explored. In addition, device attributes can 
be seen and modified, and device commands can be sent, by creating and saving a 
new dashboard.

# Generating Documentation
To re-generate the documentation locally prior to checking in updates to Git:
```bash
make docs-build html
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
* `charts/ska-mid-cbf-tdc-tmleafnode/Chart.yaml`: `version:` and `appVersion:`
* `charts/ska-mid-cbf-tdc-tmleafnode/values.yaml`: `midcbf:image:tag:`
* `charts/mid-cbf-umbrella/Chart.yaml`: 
  * `version:` and `appVersion:`
  * `version:` under `ska-mid-cbf` and `ska-mid-cbf-tdc-tmleafnode`

*Note*: `appVersion` represents the version of the application running, so it 
corresponds to the ska-mid-cbf-mcs docker image version.

Once a new release has been merged into main, create a new tag on GitLab and 
run the manual "publish-chart" stage of the tag pipeline to publish the 
Helm charts.

# Development resources

## Other resources

See more tango device guidelines and examples in the `ska-tango-examples` 
repository

## Useful commands

### Kubernetes
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
The 4 instances of the `Vcc` TANGO device servers.
* `tmcspsubarrayleafnodetestx-tmx-0`: `x` ranges from `1` to `2`. 
The 2 instances of the `TmCspSubarrayLeafNodeTest` TANGO device servers.
* `tango-host-databaseds-from-makefile-test-0`: The TANGO DB device server.
* etc.


# License

See the `LICENSE` file for details.
