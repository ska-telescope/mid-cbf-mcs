#
# Project makefile for ska-mid-cbf-mcs project. 
#
PROJECT = ska-mid-cbf-mcs

#
# Include submodule makefiles to pick up the standard Make targets;
# additional Make targets are defined in this file.
#
include .make/base.mk
include .make/k8s.mk
include .make/oci.mk
include .make/helm.mk
include .make/python.mk

# define private overrides for above variables in here
-include PrivateRules.mak

##################
# --- Python --- #
##################

# CIP-2859: Ignoring 501 which checks line length. There are over 500 failures
# for this in the code due to commenting.
# Also ignoring 503 because operators can either be before or after line break(504).
# We are choosing a standard to have it before the line break.
PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E501,W503
PYTHON_LINT_TARGET = src/ tests/
PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=./src TANGO_HOST=$(TANGO_HOST)
# unit test target(s)
PYTHON_TEST_FILE = ./tests/unit
# additional pytest flags; use -k to isolate particular tests, e.g. -k test_Scan
PYTHON_VARS_AFTER_PYTEST =
PYTHON_RUNNER = python3 -m

python-pre-lint:
	@pip3 install black isort flake8 pylint_junit typing_extensions

python-pre-build:
	@$(PYTHON_RUNNER) pip install sphinx==2.2

################
# --- Helm --- #
################

# release that all Kubernetes resources will be labelled with
HELM_RELEASE ?= test
HELM_CHART ?= ska-mid-cbf-umbrella

###############
# --- k8s --- #
###############

CI_REGISTRY ?= gitlab.com/ska-telescope/ska-mid-cbf-mcs
CI_PROJECT_DIR ?= .

# --- Taranta config --- #
# Enable jive
JIVE ?= false
# Enable Taranta
TARANTA ?= false
DASHBOARD ?= webjive-dash.dump

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

# --- k8s config --- #

CLUSTER_DOMAIN ?= cluster.local
# this assumes host and talon board 1g ethernet is on the 192.168 subnet
HOST_IP = $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | grep 192.168)
MINIKUBE ?= true
# Expose All Tango Services to the external network (enable Loadbalancer service)
EXPOSE_All_DS ?= false
SKA_TANGO_OPERATOR ?= true
# ITango enabled in ska-tango-base
ITANGO_ENABLED ?= true

K8S_CHART = $(HELM_CHART)
K8S_UMBRELLA_CHART_PATH = ./charts/ska-mid-cbf-umbrella
# defines the Kubernetes Namespace that will be deployed to using Helm
KUBE_NAMESPACE ?= ska-mid-cbf
# SDP namespace to be used
SDP_KUBE_NAMESPACE ?= ska-mid-cbf-sdp

TANGO_DATABASE = tango-databaseds-$(HELM_RELEASE)
TANGO_HOST = $(TANGO_DATABASE):10000

# integration test target(s)
K8S_TEST_FILE = ./tests/integration/controller ./tests/integration/subarray
K8S_VARS_BEFORE_PYTEST = TANGO_HOST=$(TANGO_HOST)

# additional pytest flags; use -k to isolate particular tests, e.g. -k test_Scan
K8S_VARS_AFTER_PYTEST = -s --verbose

# base64 encoded kubectl credentials for KUBECONFIG
KUBE_CONFIG_BASE64 ?=
# KUBECONFIG location
KUBECONFIG ?= /etc/deploy/config

ifneq ($(strip $(CI_JOB_ID)),)
K8S_TEST_IMAGE_TO_TEST = $(CI_REGISTRY)/ska-telescope/ska-mid-cbf-mcs/ska-mid-cbf-mcs:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-mid-cbf-mcs.midcbf.image.registry=$(CI_REGISTRY)/ska-telescope/ska-mid-cbf-mcs \
	--set ska-mid-cbf-mcs.midcbf.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
K8S_TEST_IMAGE_TO_TEST = artefact.skao.int/ska-mid-cbf-mcs:$(VERSION)
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-mid-cbf-mcs.midcbf.image.tag=$(VERSION) \
	--set ska-mid-cbf-mcs.hostInfo.hostIP="$(HOST_IP)"
endif

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.exposeAllDS=$(EXPOSE_All_DS) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-tango-base.itango.enabled=$(ITANGO_ENABLED) \
	--set ska-mid-cbf-mcs.hostInfo.clusterDomain=$(CLUSTER_DOMAIN) \
	${K8S_TEST_TANGO_IMAGE_PARAMS} \
	${TARANTA_PARAMS}

K8S_TEST_TEST_COMMAND = $(K8S_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) \
						pytest $(K8S_VARS_AFTER_PYTEST) $(K8S_TEST_FILE) \
						| tee pytest.stdout

k8s-pre-test:
	poetry export --format requirements.txt --output tests/k8s-test-requirements.txt --without-hashes --dev --with dev

k8s-do-test:
	@rm -fr build
	@mkdir -p build/logs
	@find ./tests -name "*.pyc" -type f -delete
	@echo "k8s-test: start test runner: $(K8S_TEST_RUNNER) -n $(KUBE_NAMESPACE)"
	kubectl run $(K8S_TEST_RUNNER) -n $(KUBE_NAMESPACE) --restart=Never \
	--pod-running-timeout=$(K8S_TIMEOUT) --image-pull-policy=IfNotPresent \
	--image=$(K8S_TEST_IMAGE_TO_TEST) --env=INGRESS_HOST=$(INGRESS_HOST) \
	$(PROXY_VALUES) $(K8S_TEST_RUNNER_ADD_ARGS) -iq -- sleep infinity &
	@sleep 1
	@echo "k8s-test: waiting for test runner to boot up: $(K8S_TEST_RUNNER)"
	kubectl -n $(KUBE_NAMESPACE) wait pod $(K8S_TEST_RUNNER) --for=condition=ready --timeout=$(K8S_TIMEOUT)
	@echo "k8s-test: copying in tests directory"
	kubectl -n $(KUBE_NAMESPACE) cp tests $(K8S_TEST_RUNNER):/app/tests
	@echo "k8s-test: installing requirements then executing tests..."
	@kubectl -n $(KUBE_NAMESPACE) exec $(K8S_TEST_RUNNER) -- bash -c \
		"cd /app && \
		mkdir -p build/reports && \
		sudo apt-get -qq update && \
		sudo apt-get -qq install -y --no-install-recommends python3-pip && \
		pip install --no-warn-script-location -qUr tests/k8s-test-requirements.txt && \
		$(K8S_TEST_TEST_COMMAND); \
		echo \$$? > build/status" 2>&1
	kubectl -n $(KUBE_NAMESPACE) cp $(K8S_TEST_RUNNER):/app/build/ ./build/
	kubectl get all,job,pv,pvc,ingress,cm -n $(KUBE_NAMESPACE) -o yaml > build/k8s_manifest.txt
	@echo "k8s-test: test run complete, processing logs"
	for i in $$(kubectl get pod -n $(KUBE_NAMESPACE) -o jsonpath='{.items[*].metadata.name}'); do \
	kubectl logs $$i -n $(KUBE_NAMESPACE) >> build/logs/$$i-logs.txt; \
	done;
	kubectl --namespace $(KUBE_NAMESPACE) delete --ignore-not-found pod $(K8S_TEST_RUNNER) --wait=false
	@echo "k8s-test: the test run exit code is ($$(cat build/status))"
	@exit `cat build/status`

#########################
# --- Miscellaneous --- #
#########################

jive: ## configure TANGO_HOST to enable Jive
	@echo
	@echo 'With the deployment active, copy and run the following command to configure TANGO_HOST for local jive:'
	@echo
	export TANGO_HOST=$$(kubectl describe service -n $(KUBE_NAMESPACE) $(TANGO_DATABASE)-external | grep -i 'LoadBalancer Ingress' | awk '{print $$3}'):10000

# uninstall charts, rebuild OCI image, install charts
rebuild-reinstall: k8s-uninstall-chart oci-build k8s-install-chart

help: ## show this help.
	@echo "make targets:"
	@echo "$(MAKEFILE_LIST)"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# Defines a default make target so that help is printed if make is called
# without a target
.DEFAULT_GOAL := help
.PHONY: k8s-do-test python-pre-lint python-pre-build jive rebuild-reinstall help