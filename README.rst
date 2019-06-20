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
  gui
  license

.. _description:

Description
===========

The Mid CBF MCS prototype implements at the moment these TANGO devices:

* ``CbfMaster``: Based on the ``SKAMaster`` class. It represents a primary point of contact for CBF Monitor and Control. It implements CBF state and mode indicators and a set of housekeeping commands.
* ``CbfSubarray``: Based on the ``SKASubarray`` class. It implements commands needed for scan configuration.
* ``Vcc`` and ``Fsp``: Based on the ``SKACapability`` class. These implement commands and attributes needed for scan configuration.
* ``Vcc`` and ``Fsp`` Capabilities: Based on the ``SKACapability`` class. These implement state machines to enable/disable certain VCC and FSP functionality for a scan.
    * ``VccBand1And2``, ``VccBand3``, ``VccBand4``, and ``VccBand5`` specify the operative frequency band of a VCC.
    * ``VccTransientDataCapture`` defines a search window for transient data capture during a scan.
    * ``FspCorr``, ``FspPss``, ``FspPst``, and ``FspVlbi`` specify the function mode of an FSP.
* ``FspSubarray``: Based on the ``SKASubarray`` class. It implements commands and attributes needed for scan configuration.
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

The Mid CBF MCS prototype runs in a containerised environment; the YAML configuration files ``tango.yml`` and ``mid-cbf-mcs.yml`` define the services needed to run the TANGO devices inside separate Docker containers.

To start the Docker containers, from the project root directory issue the command ::

    make build

Then ::

    make up

At the end of the procedure the command  ::

    docker ps -a

shows the list of the running containers:

* ``csplmc-cbfmaster``: the ``CbfMaster`` TANGO device
* ``csplmc-cbfsubarray``: the ``CbfSubarray`` TANGO device
* ``csplmc-tmtelstatetest``: the ``TmTelstateTest`` TANGO device
* ``csplmc-fsp``: the ``Fsp`` TANGO device
* ``csplmc-vcc``: the ``Vcc`` TANGO device
* ``csplmc-fspsubarray``: the ``FspSubarray`` TANGO device
* ``csplmc-fspcapabilities``: the ``FspCorr``, ``FspPss``, ``FspPst``, and ``FspVlbi`` TANGO devices
* ``csplmc-vcccapabilities``: the ``VccBand1And2``, ``VccBand3``, ``VccBand4``, ``VccBand5``, and ``VccTransientDataCapture`` TANGO devices
* ``csplmc-databaseds``: the TANGO DB device server
* ``csplmc-tangodb``: the MariaDB database with the TANGO database tables
* ``csplmc-rsyslog-csplmc``: the rsyslog container for the TANGO devices

To stop the Docker containers, issue the command  ::

    make down

from the project root directory.

.. _running-tests:

Running tests
=============

To run the tests in Docker containers, issue the command ::

    make test


from the project root directory.

.. _gui:

GUI
===

This prototype provides a graphical user interface, using WebJive, that runs in Docker containers defined in the configuration files ``tangogql.yml``, ``traefik.yml``, and ``webjive.yml``. To use, start the Docker containers, then navigate to ``localhost:22484/testdb``. The following credentials can be used:

* Username: ``user1``
* Password: ``abc123``

The information displayed can be customized by creating and saving a new dashboard.

.. _license:

License
=======

See the ``LICENSE`` file for details.

