#
# Project makefile for ska-mid-cbf-tdc-mcs project. 
PROJECT = ska-mid-cbf-tdc-mcs

KUBE_NAMESPACE ?= ska-mid-cbf## KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to using Helm
SDP_KUBE_NAMESPACE ?= ska-mid-cbf-tdc-sdp##namespace to be used
DASHBOARD ?= webjive-dash.dump
CLUSTER_DOMAIN ?= cluster.local

HELM_RELEASE ?= test##H ELM_RELEASE is the release that all Kubernetes resources will be labelled with

HELM_CHART ?= ska-mid-cbf-tdc-umbrella## HELM_CHART the chart name
K8S_CHART ?= $(HELM_CHART)
TANGO_DATABASE = tango-databaseds-$(HELM_RELEASE)
TANGO_HOST = $(TANGO_DATABASE):10000## TANGO_HOST is an input!

# Python variables
PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=./src:/app/src:/app/src/ska_mid_cbf_tdc_mcs KUBE_NAMESPACE=$(KUBE_NAMESPACE) HELM_RELEASE=$(RELEASE_NAME) TANGO_HOST=$(TANGO_HOST)

# CIP-2859
# Ignoring 501 which checks line length. There are over 500 failures for this in the code due to commenting. 
# Also ignoring 503 because operators can either be before or after line break(504). 
# We are choosing a standard to have it before the line break.
PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E501,W503
K8S_UMBRELLA_CHART_PATH ?= ./charts/ska-mid-cbf-tdc-umbrella

# unit and integration test targets
PYTHON_TEST_FILE = ./tests/unit/
K8S_TEST_FILE = ./tests/integration/controller ./tests/integration/subarray

# additional pytest flags; use -k to isolate particular tests, e.g. -k test_Scan
PYTHON_VARS_AFTER_PYTEST = --forked
K8S_VARS_AFTER_PYTEST = -s

CI_REGISTRY ?= gitlab.com/ska-telescope/ska-mid-cbf-tdc-mcs

CI_PROJECT_DIR ?= .

KUBE_CONFIG_BASE64 ?=  ## base64 encoded kubectl credentials for KUBECONFIG
KUBECONFIG ?= /etc/deploy/config ## KUBECONFIG location

CBF_CTRL_POD = $(shell kubectl -n $(KUBE_NAMESPACE) get pod --no-headers --selector=component=cbfcontroller-controller -o custom-columns=':metadata.name')

# this assumes host and talon board 1g ethernet is on the 192.168 subnet
HOST_IP = $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | grep 192.168) 
JIVE ?= false# Enable jive
TARANTA ?= false# Enable Taranta
MINIKUBE ?= true ## Minikube or not
EXPOSE_All_DS ?= false ## Expose All Tango Services to the external network (enable Loadbalancer service)
SKA_TANGO_OPERATOR ?= true
ITANGO_ENABLED ?= true## ITango enabled in ska-tango-base

# define private overrides for above variables in here
-include PrivateRules.mak

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
# TODO: test-makefile-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE) 
#		old name is 64 characters, too long for container name
TEST_RUNNER = test-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE)

ifneq ($(strip $(CI_JOB_ID)),)
K8S_TEST_IMAGE_TO_TEST = $(CI_REGISTRY)/ska-telescope/ska-mid-cbf-tdc-mcs/ska-mid-cbf-tdc-mcs:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-mid-cbf-tdc-tmleafnode.midcbf.image.registry=$(CI_REGISTRY)/ska-telescope/ska-mid-cbf-tdc-mcs \
	--set ska-mid-cbf-tdc-mcs.midcbf.image.registry=$(CI_REGISTRY)/ska-telescope/ska-mid-cbf-tdc-mcs \
	--set ska-mid-cbf-tdc-mcs.midcbf.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA) \
	--set ska-mid-cbf-tdc-tmleafnode.midcbf.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
PYTHON_RUNNER = python3 -m
K8S_TEST_IMAGE_TO_TEST = artefact.skao.int/ska-mid-cbf-tdc-mcs:$(VERSION)
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-mid-cbf-tdc-mcs.midcbf.image.tag=$(VERSION) \
	--set ska-mid-cbf-tdc-tmleafnode.midcbf.image.tag=$(VERSION) \
	--set ska-mid-cbf-tdc-mcs.hostInfo.hostIP="$(HOST_IP)"
endif

TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set ska-taranta-auth.enabled=$(TARANTA) \
				 --set ska-dashboard-repo.enabled=$(TARANTA)

ifneq ($(MINIKUBE),)
ifneq ($(MINIKUBE),true)
TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set ska-taranta-auth.enabled=false \
				 --set ska-dashboard-repo.enabled=false
endif
endif

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.exposeAllDS=$(EXPOSE_All_DS) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-tango-base.itango.enabled=$(ITANGO_ENABLED) \
	--set ska-mid-cbf-tdc-mcs.hostInfo.clusterDomain=$(CLUSTER_DOMAIN) \
	${K8S_TEST_TANGO_IMAGE_PARAMS} \
	${TARANTA_PARAMS}

K8S_TEST_TEST_COMMAND ?= $(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) \
						pytest \
						$(K8S_VARS_AFTER_PYTEST) $(K8S_TEST_FILE) \
						| tee pytest.stdout

PYTHON_LINT_TARGET = src/ tests/

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
include .make/base.mk
include .make/k8s.mk
include .make/oci.mk
include .make/helm.mk
include .make/python.mk

#
# Defines a default make target so that help is printed if make is called
# without a target
#
.DEFAULT_GOAL := help

jive: ## configure TANGO_HOST to enable Jive
	@echo
	@echo 'With the deployment active, copy and run the following command to configure TANGO_HOST for local jive:'
	@echo
	export TANGO_HOST=$$(kubectl describe service -n $(KUBE_NAMESPACE) $(TANGO_DATABASE)-external | grep -i 'LoadBalancer Ingress' | awk '{print $$3}'):10000

# uninstall charts, rebuild OCI image, install charts
rebuild-reinstall: k8s-uninstall-chart oci-build k8s-install-chart

k8s-pre-test:
	@kubectl exec -n $(KUBE_NAMESPACE) $(CBF_CTRL_POD) -- mkdir -p /app/mnt/talondx-config

python-pre-lint:
	@pip3 install black isort flake8 pylint_junit typing_extensions

python-pre-build:
	@$(PYTHON_RUNNER) pip install sphinx==2.2

help: ## show this help.
	@echo "make targets:"
	@echo "$(MAKEFILE_LIST)"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: all jive unit-test requirements test up down help k8s show lint logs describe mkcerts localip namespace delete_namespace ingress_check kubeconfig kubectl_dependencies helm_dependencies rk8s_test k8s_test rlint
