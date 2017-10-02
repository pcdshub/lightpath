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


Branching Logic
^^^^^^^^^^^^^^^
The most complicated logic within the lightpath is the determination of the
state of optics which control pointing between different LCLS hutches.
Obviously, whether the pointing is accurately delivered to each hutch is beyond
the scope of this module, the lightpath does try to generally determine where
beam is possible by looking at higher level EPICS variables. The device capable
of steering beam between forks in the path can be found with
:attr:`.BeamPath.branches`. Each should implement; ``branches``, all possible
beamline destinations for the optic, and ``destination``, a list of current
beamlines the device could be sending beam along. When the :class:`.BeamPath`
object finds an incontinuous beamline, it checks a list of upstream optics to
make sure that they all agree upon the destination. For instance, to deliver
beam down the **MFX** line, both ``XRT M1`` and ``XRT M2`` must have **MFX** in
their list of destinations. After this split, these optics are ignored so that
each branching device only has to list the possible destinations that come
immediattely after it. For example, the **XPP** LODCM should not have to report
that it is ready to deliver beam to every possible **FEH** destination, only
whether it is inserted for XPP operations or out of the **HXR** beampath. 

MPS Information
^^^^^^^^^^^^^^^


