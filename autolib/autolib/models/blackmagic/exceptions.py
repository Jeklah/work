"""
Exception classes for indicating fatal errors communicating with the Hyperdeck series of SDI / HDMI recorders.
"""

from autolib.models.deviceexception import DeviceException


class HyperDeckException(DeviceException):
    """
    Exceptions relating the the Blackmagic Designs Hyperdeck Studio controller.
    """
    pass
