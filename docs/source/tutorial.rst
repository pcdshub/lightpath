Introduction
************

Device Manipulation
^^^^^^^^^^^^^^^^^^^
The lightpath abstracts control of multiple devices into a single beampath
object. Actual device instantiation should be handled else where the lightpath
just assumes that you give it a list of devices that match the
:class:`.LightInterface`. For now we can demonstrate the basic features of the
API by using a simulated path.

.. ipython:: python

   import lightpath.tests

   # Return a simple simulated path
   path = lightpath.tests.path()

   # Return a mock lcls facility
   lcls = lightpath.tests.lcls()

You can look at all the devices in the path, either by looking at the objects
themselves or using the :meth:`.BeamPath.show_devices`

.. ipython:: python

   path.show_devices()

   path.devices


Now lets insert some devices and see how we can quickly find what is blocking
the instrument. The lightpath module differentiates between two kinds of
inserted devices, ``blocking`` and ``incident``. The first is a device that
will prevent beam from transmitting through it i.e a stopper or YAG. The second
includes slightly more complex, but essentially is any device that can be
inserted in to the beam, but won't greatly affect operation i.e an IPIMB. The
difference between the two is determined by comparing the devices
``transmission`` attribute against :attr:`.BeamPath.minimum_transmission`.

Note that these simulated devices have ``.insert()`` and ``.remove()`` methods for
convenience of testing, but real devices may not.

.. ipython:: python

   path.cleared

   path.five.insert()

   path.six.insert()

   path.cleared

   path.incident_devices

   path.blocking_devices

   path.show_devices()


The most upstream blocking device by checking the :attr:`.BeamPath.impediment`

.. ipython:: python

   path.impediment == path.six

   path.two.insert()

   path.impediment == path.two

   path.blocking_devices


Branching Logic, and Graph Construction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In order to determine the state of the "beamline", Lightpath must first
understand where the various devices lie along the beam path.  Lightpath does
this by constructing a Directed Graph with the devices as nodes. This
formulation allows Lightpath to find any and all valid paths to any given
device, given the state of the facility at that time.

In order to do this, each device considered by lightpath must carry with
it the following metadata:

* input branches
* output branches
* z-position

This is the minimum information needed to place a device in the facility graph.
To simplify matters for the user, lightpath orders devices on the same
branch by their z-position, or distance from the light source.

For more implementation details (device API, happi database information)
see the :ref:`interface_api` section

LCLS Specific Notes
^^^^^^^^^^^^^^^^^^^

.. figure:: ../static/LCLS_beamline_map.svg
   :width: 100%
   :alt: Schematic of LCLS facility, with branch names (red) and
         branching devices (blue) labeled.

The way Lightpath organizes devices (ordering devices on the same branch
by z position) is greatly motivated by the LCLS facility and its naming
conventions.  LCLS recently adopted a device naming convention that
relies heavily on this concept of branches, with branch names changing
at branching devices.
