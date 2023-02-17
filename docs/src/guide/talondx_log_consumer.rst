**************************
Talon DX Log Consumer
**************************
The Talon DX Log Consumer is a Tango device intended to run on the host machine that connects
to the Talon-DX boards. This Tango device is set up as a default logging target for all the
Tango device servers running on the HPS of each Talon-DX board. When the HPS device servers
output logs via the Tango Logging Service, the logs get transmitted to this log consumer device
where they get converted to the SKA logging format and outputted once again via the
SKA logging framework. In this way logs from the Talon-DX boards can be aggregated in once
place and eventually shipped to the Elastic framework in the same way as logs from the Mid CBF
Monitor and Control Software (MCS).

Note: more instances of the device may be created to provide enough bandwidth for all the HPS device servers.


Connecting from HPS DS to the Log Consumer
##########################################
The Talon-DX boards connect to the host machine (currently known as the Dell Server) over
a single Ethernet connection. The IP address of the Dell Server on this connection is
``169.254.100.88`` and all outgoing traffic from the Talon-DX boards must be addressed to this IP.

When the log consumer starts up on the Dell server, the OmniORB end point (IP address and port) it is assigned
is local to the Dell server (i.e. IP address ``142.73.34.173``, arbitrary port). Since the Talon
boards are unable to connect to this IP address. we need to manually publish a different
endpoint when starting up the log consumer that is visible to the HPS devices.

The following ORB arguments are used (see the make target ``talondx-log-consumer``):

* ``-ORBendPointPublish giop:tcp:169.254.100.88:60721``: Exposes this IP address and port to all clients of this Tango device. When the HPS device servers contact the database to get the network information of the log consumer, this is the IP address and port that is returned. The IP addresses matches that of the Ethernet connection to the Dell server, allowing the HPS device servers to direct their messages across that interface.
* ``-ORBendPoint giop:tcp:142.73.34.173:60721``: Assigns the IP address and port that the log consumer device is actually running on. This needs to be manually assigned since an iptables mapping rule was created on the Dell server to route any TCP traffic coming in on ``169.254.100.88:60721`` to ``142.73.34.173:60721``.

Some important notes:

* Due to the end point publishing, no Tango devices running on the Dell server will be able to connect to the log consumer (including being able to configure the device from Jive). This is because the published IP address is not accessible on the Dell server. There may be a way to publish multiple endpoints, but this needs further investigation.
* If the log consumer device cannot be started due to an OmniORB exception saying that the end point cannot be created, it is possible that the ``142.73.34.173`` needs to change to something else. It is not yet clear why this can happen. To change it do the following:

  * Remove the ORB arguments from the ``talondx-log-consumer`` make target, and then start the log consumer.
  * Open up Jive and look at what IP address is automatically assigned to the log consumer device. This is the IP address that we now need to use for the endpoint.
  * Find the iptables rule that maps ``169.254.100.88:60721`` to ``142.73.34.173:60721``, and change it to the new IP address.
  * Add the ORB arguments back in, using the correct IP address for the end point.
