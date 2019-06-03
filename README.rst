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

The Mid CBF MCS prototype implements at the moment these TANGO devices:

* ``CbfMaster``: Based on the ``SKAMaster`` class. It represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a set of housekeeping commands.
* ``CbfSubarray``: Based on the ``SKASubarray`` class. It implements commands needed for scan configuration.
* ``Vcc`` and ``Fsp``: Based on the ``SKACapability`` class. These simulate the Mid CBF Capabilities to test basic functionality.
* ``TmTelstateTest``: Based on the ``SKABaseDevice`` class. It simulates the TM TelState, providing regular updates to parameters during scans using a publish-subscribe mechanism.

.. _getting-started:

Getting started
===============

The project can be found in the SKA GitHub repository.

To get a local copy of the project::

    git clone https://github.com/ska-telescope/mid-cbf-mcs.git

.. _how-to-run:

How to run
==========

The Mid CBF MCS prototype runs in a containerised environment; the YAML configuration file ``docker-compose.yml`` defines the services needed to run the TANGO devices inside separate Docker containers.

From the project root directory issue the command ::

    make up

At the end of the procedure the command  ::

    docker ps -a


shows the list of the running containers:

* ``csplmc-cbfmaster``: the ``CbfMaster`` TANGO device
* ``csplmc-cbfSubarray``: the ``CbfSubarray`` TANGO device
* ``csplmc-tmtelstatetest``: the ``TmTelstateTest`` TANGO device
* ``csplmc-fsp``: the ``Fsp`` TANGO device
* ``csplmc-vcc``: the ``Vcc`` TANGO device
* ``csplmc-databaseds``: the TANGO DB device server
* ``csplmc-tangodb``: the MariaDB database with the TANGO database tables
* ``csplmc-rsyslog-csplmc``: the rsyslog container for the TANGO devices

To stop the Docker containers, issue the command  ::

    make down

from the project root directory.

.. _running-tests:

Running tests
=============

To run the test in Docker containers, issue the command ::

    make test


from the project root directory.

.. _license:

License
=======

See the ``LICENSE`` file for details.

