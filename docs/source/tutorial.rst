Introduction
************
The lightpath abstracts control of multiple devices into a single beampath
object. Actual device instantiation should be handled else where the lightpath
just assumes that you give it a list of devices that match the
:class:`.LightInterface`. For now we can demonstrate the basic features of the
API by using a simulated path.

.. ipython:: python

   import lightpath.tests

   #Return the simulated path
   path = lightpath.tests.path()

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
``transmission`` attribute against :attr:`.BeamPath.minimum_transmission`

.. ipython:: python

   path.cleared

   path.five.insert()
   
   path.six.insert()

   path.cleared

   path.incident_devices
   
   path.blocking_devices


The most upstream blocking device by checking the :attr:`.BeamPath.impediment`

.. ipython:: python

   path.impediment == path.six

   path.two.insert()

   path.impediment == path.two

   path.blocking_devices


Each device can be accessed and removed individually, or you can use the
:meth:`.BeamPath.clear`. The method has a few hooks to control which devices
you actually want to remove.

.. ipython:: python

   path.clear(passive=False)

   path.incident_devices

   path.clear(passive=True)
   
   path.incident_devices

MPS Information
^^^^^^^^^^^^^^^


