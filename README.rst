.. HOME SECTION ==================================================

.. Hidden toctree to manage the sidebar navigation.

.. toctree::
  :maxdepth: 1
  :caption: Home
  :hidden:


.. COMMUNITY SECTION ==================================================

.. Hidden toctree to manage the sidebar navigation.

.. toctree::
  :maxdepth: 1
  :caption: Community
  :hidden:

=============
Mid CBF
=============

.. toctree::
  :maxdepth: 1

  description
  getting-started
  how-to-run
  running-tests
  license

.. _description:

Description
===================

The CSP.LMC prototype implements at the moment two TANGO devices:

* the ``CbfMaster`` device: based on the ``SKAMaster`` class, it represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a limited set of housekeeping commands.
* the ``CbfSubarray`` device: based on the ``SKASubarray`` class, it implements commands needed for scan configuration.

.. _getting-started:

Getting started
===============

The project can be found in the SKA GitHub repository.

To get a local copy of the project::

    git clone https://github.com/ska-telescope/mid-cbf-mcs.git

.. _how-to-run:

How to run
==========

The CSP.LMC prototype runs in a containerised environment: the YAML configuration file ``docker-compose.yml`` includes the stages to run the the CSP.LMC TANGO devices inside separate docker containers.

From the project root directory issue the command ::

    make up

At the end of the procedure the command  ::

    docker ps -a


shows the list of the running containers:

* ``csplmc-tangodb``: the MariaDB database with the TANGO database tables
* ``csplmc-databaseds``: the TANGO DB device server
* ``csplmc-cbfmaster``: the ``CbfMaster`` TANGO device
* ``csplmc-cbfSubarray``: the ``CbfSubarray`` TANGO device
* ``csplmc-vcc``: the ``VCC`` TANGO device (currently only for testing purposes)
* ``csplmc-fsp``: the ``FSP`` TANGO device (currently only for testing purposes)
* ``csplmc-rsyslog-csplmc``: the rsyslog container for the CSP.LMC devices

To stop the Docker containers, issue the command  ::

    make down

from the prototype root directory.

.. _running-tests:

Running tests
=============

To run the test in Docker containers, issue the command ::

    make test


from the root project directory.

.. _license:

License
=======

See the ``LICENSE`` file for details.

