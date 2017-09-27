LCLS Lightpath
==============
.. image:: https://travis-ci.org/slaclab/lightpath.svg?branch=master
    :target: https://travis-ci.org/slaclab/lightpath

.. image:: https://codecov.io/github/slaclab/lightpath/coverage.svg?branch=master
    :target: https://codecov.io/gh/slaclab/lightpath?branch=master

Python module for control of LCLS beamlines

By abstracting individual devices into larger collections of paths, operators
can quickly guide beam to experimental end stations. Instead of dealing with
the individual interfaces for each device, devices are summarized in states.
This allows operators to quickly view and manipulate large sections of the
beamline when the goal is to simply handle beam delivery.

Conda
++++++

Install the most recent tagged build:

.. code::

  conda install lightpath -c skywalker-tag -c lightsource2-tag -c conda-forge -c paulscherrerinstitute

Install the most recent development build:

.. code::

  conda install lightpath -c skywalker-dev -c lightsource2-tag -c conda-forge -c paulscherrerinstitute
