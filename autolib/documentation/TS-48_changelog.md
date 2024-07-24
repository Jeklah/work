# TS-48 changes

## Breaking changes

 * The Analyser has been largely rewritten to use the RestBoilerPlate metaclass and to add a hierarchy to the API and 
   replace some odd approaches with simpler / more idiomatic approaches.
 * Some unnecessary complexity has been removed from the Qx (the constructor taking hostname or ipaddress keywords etc.)
 * The loudness methods have been moved / rewritten in models/qxseries/loudness.py using RestBoilerPlate.

## Other changes

 * I've created an extended metaclass RestBoilerPlate for quickly wrapping Rest APIs. You can add properties (getters
   and setters for individual settings on the device exposed by a path with no path parameters) or methods
   (parameterised gets and sets for URLs that contain path parameters). This hugely reduces http handling boilerplate 
   and eases the creation of unit tests). 
 * Unit testing is now easier as the requests module can be selectively overridden to mock responses.
 * Timeouts are now currently applied to the Rest API wrappers through thanks to the changed to how requests is used 
   and with the help of partial functions.
 * The RestBoilerPlate metaclass has helped make a clear split between the http communication with the device and the 
   interpretation of the responses.
 * Fixed project dependencies by removing the versions from the requirements.txt file - though this will need revisiting
   to find a way to maintain the versions without making it impossible to install on newer Python versions (pinned 
   packages that contain native code are sometimes not able to be compiled on later versions of Python).
 * Some core unit tests have been added (to the metaclass, the ArtifactArchiveFolder and it's factory, NMOS etc.)
 * The Qx, QxL and HyperdeckStudio classes now implement the DeviceController interface. This will provide some 
   fundamental methods (e.g. reboot, upgrade etc.) that a device must support.
 * It's not a test framework. It's a control, configure and inspect system. An automation system. pytest is the test
   system. Hence the rename from test_system to autolib
 * The documentation builder correctly uses the metaclass when generating API reference documentation. Properties
   are documented once for get and set, methods can have a docstring per operation.
 * There's been some furniture moves to generalise things that were Qx-specific (e.g. SSHUtil) though these should not
   be breaking changes.
 * The NMOS wrapper has been reimplemented using the new RestBoilerPlater metaclass.
