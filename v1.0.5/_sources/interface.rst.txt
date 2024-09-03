.. _interface_api:

================
Device Interface
================

To make loading and updating lightpath as simple as possible, lightpath
relies on two external sources of information:

1. A database definition of the device (static, ``happi``)
2. A snapshot of the device's current status (dynamic, ``ophyd``)

The first of these two is simple to understand, this information allows us
to properly place the device in the facility relative to the other devices.
The second, device status, allows us to see where the device is pointing and
if it is permitting beam at a given point in time.

The static information is held in the ``happi`` database, while the dynamic
information is read from the device's ``ophyd`` representation.

Database Definition
-------------------

An example of a valid lightpath happi definition:

.. code-block:: console

    +------------------+-------------------------------------------------------------------------+
    | EntryInfo        | Value                                                                   |
    +------------------+-------------------------------------------------------------------------+
    | active           | True                                                                    |
    | args             | ['{{prefix}}']                                                          |
    | beamline         | LFE                                                                     |
    | creation         | Mon Jul 18 16:05:21 2022                                                |
    | device_class     | pcdsdevices.attenuator.FEESolidAttenuator                               |
    | documentation    | None                                                                    |
    | functional_group | N/A                                                                     |
    | input_branches   | ['L0']                                                                  |
    | ioc_arch         | None                                                                    |
    | ioc_engineer     | None                                                                    |
    | ioc_hutch        | None                                                                    |
    | ioc_location     | None                                                                    |
    | ioc_name         | None                                                                    |
    | ioc_release      | None                                                                    |
    | ioc_type         | None                                                                    |
    | kwargs           | {'input_branches': '{{input_branches}}', 'name': '{{name}}',            |
    |                  | 'output_branches': '{{output_branches}}'}                               |
    | last_edit        | Mon Jul 18 16:05:21 2022                                                |
    | lightpath        | True                                                                    |
    | location_group   | N/A                                                                     |
    | name             | at2l0                                                                   |
    | output_branches  | ['L0']                                                                  |
    | prefix           | AT2L0:XTES                                                              |
    | stand            | L0S07                                                                   |
    | type             | pcdsdevices.happi.containers.LCLSLightpathItem                          |
    | z                | 734.50000                                                               |
    +------------------+-------------------------------------------------------------------------+

An example container has been included in lightpath as
``lightpath.happi.containers.LightpathItem``, and is discoverable via python
entrypoints.  In this example, the database information is used to instantiate
the device by being passed in as a keyword argument.

LCLS modifies this container slightly, adding LCLS-relevant metadata and the
option to omit the ``input_branches`` / ``output_branches`` keyword arguments
for devices that do not implement the LightpathInterface.  (see
``pcdsdevices.happi.containeres.LCLSLightpathItem``)

Device Status (Lightpath Status)
--------------------------------

What does your ophyd device need?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the simplest sense, your device needs to present the following API:

* ``device.lightpath_summary``: a signal that changes whenever the
  Lightpath-state of the device changes
* ``device.get_lightpath_state()``: a method that returns a
  :class:`lightpath.LightpathState` dataclass instance, containing the
  Lightpath-state of the device

How is this implemented?
^^^^^^^^^^^^^^^^^^^^^^^^

The main point of interaction between Lightpath and a device's dynamic
information should be the ``get_lightpath_state()`` method.  This method is
expected to return a dataclass with the following fields:

* **inserted**: if the device is inserted
* **removed**: if the device is removed
* **output**: a dictionary mapping an output branch name to the transmission
  being delivered to that branch

Lightpath also subscribes to a signal called ``lightpath_summary``, which is
expected to change whenever the lightpath status of the device has changed.
When Lightpath sees a change in this signal, it will query ``get_lightpath_state()``
for the updated status of the device.  (Lightpath may also query
``get_lightpath_state()`` at other points).

Putting all of this together, a minimal device definition that fulfills the
lightpath interface requirements might look like:

.. code-block:: python

    from lightpath import LightpathState
    from ophyd import Device, EpicsSignal
    from ophyd import Component as Cpt

    class MyDevice(Device):

        # if we were to only care about one signal
        lightpath_summary = Cpt(EpicsSignal, ':MY:PV')

        input_branches = ['K0']
        output_branches = ['K0']

        def get_lightpath_state(self):
            return LightpathState(
                inserted=True,
                removed=True,
                output={self.output_branches[0]: 1}
            )

This would work, strictly speaking, but is far from being optimized and easy to use.

To make things easier, LCLS has implemented this as an ophyd device mixin in
``pcdsdevices.interfaces.LightpathMixin``.  Notably, this mixin caches the
lightpath state, so that calls to ``get_lightpath_state()`` do not overwhelm
the ophyd callback queue with Channel Access requests.  This was found to be
necessary for beam paths with many devices.

In LCLS, you might see a device object definition that looks like the
following:

.. code-block:: python

    from lightpath import LightpathState
    from pcdsdevices.interface import LightpathMixin
    from ophyd import Device

    class BaseDevice(Device, LightpathMixin):
        """
        Base class for some specific device
        """
        # Mark as parent class for lightpath interface
        lightpath_cpts = ['xwidth.user_readback', 'ywidth.user_readback']

        nominal_aperature = 0.5

        # < ... unrelated methods snipped ... >

        def calc_lightpath_state(
            self,
            xwidth: float,
            ywidth: float
        ) -> LightpathState:
            widths = [xwidth, ywidth]
            self._inserted = (min(widths) < self.nominal_aperture)
            self._removed = not self._inserted
            self._transmission = 1.0 if self._inserted else 0.0

            return LightpathState(
                inserted=self._inserted,
                removed=self._removed,
                output={self.output_branches[0]: self._transmission}
            )

In this case we are leveraging the ``LightpathMixin`` class, which does most of
the repetitive setup for us (creating ``lightpath_summary`` signal, subscribing
to relevant components, setting up lightpath state caching, checking that the
subclass is correctly configured, etc.).  This mixin delegates the calculation
of the lightpath state to the ``calc_lightpath_state`` method, which is to be
written by the device creator.  Furthermore, the mixin looks for a list of
component names called ``lightpath_cpts``, which will ``lightpath_summary``
will watch for changes.  Upon a change in one of these signals, the
LightpathMixin will get the values of each component and pass them to
``calc_lightpath_state``.
