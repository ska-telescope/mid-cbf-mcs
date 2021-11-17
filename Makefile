#
# Project makefile for ska-mid-cbf-mcs project. You should normally only need to modify
# DOCKER_REGISTRY_USER and PROJECT below.
#

#
# DOCKER_REGISTRY_HOST, DOCKER_REGISTRY_USER and PROJECT are combined to define
# the Docker tag for this project. The definition below overwrites
# DOCKER_REGISTRY_USER and PROJECT
#
#DOCKER_REGISTRY_USER:=ska-docker
PROJECT = ska-mid-cbf-mcs

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-cbf
SDP_KUBE_NAMESPACE ?= sdp #namespace to be used
DASHBOARD ?= webjive-dash.dump

# HELM_RELEASE is the release that all Kubernetes resources will be labelled
# with
HELM_RELEASE ?= test

# HELM_CHART the chart name
HELM_CHART ?= ska-mid-cbf-umbrella

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
UMBRELLA_CHART_PATH ?= charts/ska-mid-cbf-umbrella/

# Fixed variables
# Timeout for gitlab-runner when run locally
TIMEOUT = 86400
# Helm version
HELM_VERSION = v3.3.1
# kubectl version
KUBERNETES_VERSION = v1.19.2

# Docker, K8s and Gitlab CI variables
# gitlab-runner debug mode - turn on with non-empty value
RDEBUG ?=
# gitlab-runner executor - shell or docker
EXECUTOR ?= shell
# DOCKER_HOST connector to gitlab-runner - local domain socket for shell exec
DOCKER_HOST ?= unix:///var/run/docker.sock
# DOCKER_VOLUMES pass in local domain socket for DOCKER_HOST
DOCKER_VOLUMES ?= /var/run/docker.sock:/var/run/docker.sock
# registry credentials - user/pass/registry - set these in PrivateRules.mak
CAR_OCI_REGISTRY_USER_LOGIN ?=  ## registry credentials - user - set in PrivateRules.mak
CI_REGISTRY_PASS_LOGIN ?=  ## registry credentials - pass - set in PrivateRules.mak
CI_REGISTRY ?= gitlab.com/ska-telescope/ska-mid-cbf-mcs

CI_PROJECT_DIR ?= .

KUBE_CONFIG_BASE64 ?=  ## base64 encoded kubectl credentials for KUBECONFIG
KUBECONFIG ?= /etc/deploy/config ## KUBECONFIG location


XAUTHORITYx ?= ${XAUTHORITY}
THIS_HOST := $(shell ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY := $(THIS_HOST):0

# define private overrides for above variables in here
-include PrivateRules.mak

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
# TODO: test-makefile-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE) 
#		old name is 64 characters, too long for container name
TEST_RUNNER = test-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE)

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
include .make/release.mk
include .make/k8s.mk

#
# Defines a default make target so that help is printed if make is called
# without a target
#
.DEFAULT_GOAL := help

requirements: ## Install Dependencies
	python3 -m pip install -r requirements.txt

unit-test: ## Run simulation mode unit tests
	@mkdir -p build; \
	pytest -c setup-unit-test.cfg

jive: ## configure TANGO_HOST to enable Jive
	@echo
	@echo 'With the deployment active, copy and run the following command to configure TANGO_HOST for local jive:'
	@echo
	export TANGO_HOST=$$(minikube ip):$$(kubectl describe service -n $(KUBE_NAMESPACE) $(TANGO_DATABASE) | grep -i 'NodePort:' | awk '{print $$3}' | sed 's;/TCP;;')

update-db-port:  ## update Tango DB port so that the DB is accessible from the Talon boards on the Dell server
	kubectl -n ska-mid-cbf patch service/tango-host-databaseds-from-makefile-test --type='json' -p '[{"op":"replace","path":"/spec/ports/0/nodePort","value": 30176}]'

# pull and interactive preserved from docker.mk
###############################################
# pull:  ## download the application image
# 	docker pull $(IMAGE_TO_TEST)

# # piplock: build  ## overwrite Pipfile.lock with the image version
# # 	docker run $(IMAGE_TO_TEST) cat /app/Pipfile.lock > $(CURDIR)/Pipfile.lock

# interactive:  ## start an interactive session 
# 	docker run --rm -it -p 3000:3000 --name=$(CONTAINER_NAME_PREFIX)dev -e TANGO_HOST=$(TANGO_HOST)  -v $(CURDIR):/app $(IMAGE_TO_TEST) /bin/bash
###############################################

#pytest $(if $(findstring all,$(MARK)),, -m '$(MARK)')

.PHONY: all jive unit-test requirements test up down help k8s show lint logs describe mkcerts localip namespace delete_namespace ingress_check kubeconfig kubectl_dependencies helm_dependencies rk8s_test k8s_test rlint
