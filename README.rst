LCLS Lightpath
==============
Python module for control of LCLS beamlines

By abstracting individual devices into larger collections of paths, operators
can quickly guide beam to experimental end stations. Unlike it's predecessors,
this renditon is based entirely in Python with a Python IOC publishing relevant
informatoin over Channel Access. This gives users the option to either use a
GUI based solution or simply use the command line to control beamline states. 

In addition, this version of the LCLS Lightpath includes the MPS system so that
faults can be observed in the same place devices are controlled.
