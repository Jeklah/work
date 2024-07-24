"""\
Currently the QxP class is functionally identical to the QxL.
"""
from autolib.models.qxseries.qxl import QxL


class QxP(QxL):
    """\
    This class can be used to configure, control and inspect a QxP.
    """

    @property
    def essential_processes(self):
        return 'qx_server', 'qx_displayclient'
