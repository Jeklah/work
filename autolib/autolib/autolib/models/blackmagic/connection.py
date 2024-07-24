"""
Protocol connection object for communicating with a HyperDeck series SDI / HDMI recorder.
"""

import logging
from socket import socket, AF_INET, SOCK_STREAM

import select

import autolib.models.blackmagic.protocol as protocol
from autolib.logconfig import autolib_log
from autolib.models.blackmagic.exceptions import HyperDeckException


class HyperDeckConnection:
    """
    An IPv4 connection to a HyperDeckStudio device. This connection is currently send->wait for response->send->etc.
    rather than threaded. This is to simplify the communication with the device and as a result it means we do not
    register for unsolicited tallies (they're all disabled). A future change to this connection may be to enable a
    listener thread but until we have proven that the protocol allows us to clearly distinguish between responses,
    it will remain like this. The readback from the device is performed in the send_message() method straight after
    the Message is sent. Currently there is no support for unsolicited notifications - though this is planned.
    """

    def __init__(self, ip_address, ip_port=9993):
        """
        Create the connection (TCP/IPv4) to the HyperDeck Studio device using the specified IP address. The port
        for communication is 9993 in the current implementation of the protocol.

        :param ip_address: String containing the IP.
        """

        self._connected = False
        self._socket = None
        self._log = self.log = logging.getLogger(autolib_log)
        self._ip_address = ip_address
        self._ip_port = ip_port

        self.config = {'configuration': {}, 'slot_info': {}, 'device_info': {}, 'transport_info': {}}
        self.clips = {}
        self._response_handler = {
            200: self._handle_ok,
            202: self._handle_slot_info,
            204: self._handle_device_info,
            205: self._handle_clips_get,
            208: self._handle_transport_info,
            209: self._handle_notify,
            210: self._handle_remote,
            211: self._handle_configuration,
            500: self._handle_initial,
        }

    def __enter__(self):
        """
        Context manager support - when the connection is used in a with statement block, the connect() method is
        called upon entering the statement block.
        """
        self.connect()
        return self

    def __exit__(self, *args, **kwargs):
        """
        Context manager support - when the connection is used in a with statement block, the connect() method is
        called upon exiting the statement block.
        """
        self.disconnect()

    def __del__(self):
        """
        When this connection object is deleted, ensure that we've told the Hyperdeck to quit the session and that we
        have subsequently closed the transport layer connection.
        """
        self.disconnect()

    @property
    def connected(self):
        return self._connected

    def _connect_transport(self):
        """
        Attempt to connect to the socket using the ip address and port specified during construction.
        :return: Current connection state (True = connected otherwise False)
        """
        self._log.info(f"Creating socket, ip: {self._ip_address}, port: {self._ip_port}")
        self._socket = socket(AF_INET, SOCK_STREAM)

        try:
            self._socket.connect((self._ip_address, self._ip_port))
        except OSError as e:
            self._log.warning(f"Failure to connect to {self._ip_address} port {self._ip_port}. Exception type is {e}")
            self._connected = False
            return False

        self._connected = True
        return True

    def _disconnect_transport(self):
        """
        Close the socket.
        """
        self._socket.close()
        self._connected = False

    def _send_transport(self, send_buffer: bytes) -> int:
        """
        Send the provided byte array to the socket.
        :param send_buffer: Bytes to send.
        :return: The number of bytes sent.
        """
        self._log.debug(f"Sending: {send_buffer}")
        return self._socket.send(send_buffer)

    def _receive_transport(self, read_size: int, timeout: float = 2.0) -> bytes:
        """
        Attempt to read from the socket, timing out after a specified number of seconds.
        :param read_size: Maximum number of bytes to read from the socket.
        :param timeout: Read timeout in seconds (default = 2 seconds)
        :return: The read byte array.
        """
        self._socket.setblocking(False)

        ready = select.select([self._socket], [], [], timeout)
        if ready[0]:
            read_buffer = self._socket.recv(read_size)
            self._log.debug(f"Read: {read_buffer}")
            return read_buffer

    def _handle_ok(self, response_obj):
        """
        Handle OK (200) responses from the Hyperdeck.
        """
        pass

    def _handle_slot_info(self, response_obj):
        """
        Update the stored slot_info dictionary in the main _config dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self.config['slot_info'].update(response_obj.params)

    def _handle_clips_get(self, response_obj: protocol.HyperDeckResponse):
        """
        Update the _clips dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self._clips = response_obj.params.copy()

    def _handle_transport_info(self, response_obj: protocol.HyperDeckResponse):
        """
        Update the stored transport_info dictionary in the main _config dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self.config['transport_info'].update(response_obj.params)

    def _handle_notify(self, response_obj: protocol.HyperDeckResponse):
        """
        If any notifications are enabled, turn them off again. The protocol handler does not currently work with
        unsolicited status update messages.

        :param response_obj: Response object received by the connection.
        """
        for notification, state in response_obj.params.items():
            if state == b'true':
                self.send_message(protocol.notify(transport=False, slot=False, configuration=False))
                break

    def _handle_remote(self, response_obj: protocol.HyperDeckResponse):
        """
        If remote control is disabled, re-enable it.

        :param response_obj: Response object received by the connection.
        """
        if response_obj.get("enabled", None) in [None, b'false']:
            self.send_message(protocol.remote(enable=True))

    def _handle_device_info(self, response_obj: protocol.HyperDeckResponse):
        """
        Update the stored device_info dictionary in the main _config dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self.config['device_info'].update(response_obj.params)

    def _handle_initial(self, response_obj: protocol.HyperDeckResponse):
        """
        Following an initial connection status update message, update the stored device_info dictionary in the main
        _config dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self.config['device_info'].update(response_obj.params)

    def _handle_configuration(self, response_obj: protocol.HyperDeckResponse):
        """
        Update the stored configuration dictionary in the main _config dictionary based on the provided response object.

        :param response_obj: Response object received by the connection.
        """
        self.config['configuration'].update(response_obj.params)

    def send_bytes(self, message_obj: protocol.HyperDeckResponse):
        """
        Send a HyperDeckMessage command object via the transport layer to the device as bytes.

        :param message_obj: A HyperDeckMessage object
        :return: A tuple containing the bytes sent and the expected response ID.
        """
        bytes_sent = self._send_transport(bytes(message_obj))
        return bytes_sent, message_obj.expects

    def read_response(self):
        """
        Read a HyperDeck response object via the transport layer from the device following a message send.

        :return: A HyperDeck response object.
        """
        byte_buffer = bytearray()

        while True:
            bytes_read = self._receive_transport(protocol.REPLY_SIZE, 0.1)
            if bytes_read is not None and len(bytes_read) > 0:
                byte_buffer += bytes_read
            else:
                break

        return protocol.HyperDeckResponse(byte_buffer)

    def process_response(self, response):
        """
        Dispatch the supplied response object to the appropriate handler method by indexing the handler function
        by response ID in the _response_handler dictionary.

        :param response: HyperDeck response object
        """
        if response.code:
            if response.code in self._response_handler.keys():
                self._log.debug(repr(response))
                handler = self._response_handler.get(response.code, None)
                if handler:
                    handler(response)
                else:
                    self._log.error(f"No handler configured for response type {response.code}")
            elif 100 <= int(response.code) <= 199:
                self._log.error(f"Some error has occurred: {repr(response)}")
            else:
                self._log.warning(f"Unhandled response: {response.code}")

    def send_message(self, message_obj, timeout=5):
        """
        Send a message object to the connection and read and process replies until the expected reply is encountered.
        If it has not been received before the timeout, then throw an exception.

        :param message_obj: The message object to send
        :param timeout: Timeout in seconds
        :return: The response object that we expected or None.
        """
        sent_bytes, expected_id = self.send_bytes(message_obj)

        response = self.read_response()
        if response:
            expected = response.code == expected_id
            if not expected:
                self._log.error(f"Unexpected response: {repr(response)}")
            self.process_response(response)
            return expected, response
        self._log.error("No response received (likely an error)")
        return False, None

    def connect(self):
        """
        Connect to the HyperDeck Studio and obtain it's initial state and clip list.
        """
        self._connect_transport()

        if self._connected:
            status_success = []
            configure_success = []

            # Read the initial 500 message
            status_success.append(protocol.HyperDeckResponse(self._receive_transport(protocol.REPLY_SIZE, 3)))

            # Read the status of the device to get a set of initial values
            status_success.append(self.send_message(protocol.deviceinfo())[0])
            status_success.append(self.send_message(protocol.slotinfo())[0])
            status_success.append(self.send_message(protocol.transportinfo())[0])
            status_success.append(self.send_message(protocol.configuration())[0])
            status_success.append(self.send_message(protocol.clipsget())[0])

            # Turn on all notifications as the protocol is very difficult to parse without writing a full parser that
            # handles all response types individually (there's no command terminator) and so to guard against multiple
            # responses being received, it's safer to turn everything else off. In the future, a full PLY parser could
            # be written but that seems overkill right now.
            configure_success.append(self.send_message(protocol.notify(transport=False, slot=False, configuration=False))[0])

            # Finally turn on remote control.
            configure_success.append(self.send_message(protocol.remote(enable=True))[0])

            if False in status_success:
                self._log.error("Could not obtain status for the unit")

            if False in configure_success:
                raise HyperDeckException("Could not configure the unit")
        else:
            raise HyperDeckException("Could not connect to the unit")

    def disconnect(self):
        """
        Disconnect from the socket
        """
        # In disconnect(), explicitly send a quit message to doubly ensure we don't totally own the
        # resource.
        self.send_message(protocol.quit_session())
        self._disconnect_transport()
