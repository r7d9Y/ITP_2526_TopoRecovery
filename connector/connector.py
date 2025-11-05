r"""
      _____________________________________________
     __/___  ____/\__/ ______ \____/ /\____/ /\___
    ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
   ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
  ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
 ______/_/\/_____/_/\/___\\_\______/_/\/______
_______\_\/______\_\/_____|_|______\_\/______
"""

import re
from typing import Tuple, List
from netmiko import ConnectHandler
from enum import Enum, auto


class ExecMode(Enum):
    """
    Enumeration for different execution modes on a Cisco IOS network device
    """
    USER_EXEC = auto()
    GLOBAL_EXEC = auto()
    PRIVILEGED_EXEC = auto()


class Connector:
    """
    Connector class to manage telnet connections to (virtual) network devices using the Netmiko library
    """

    def __init__(self, device_type: str, ip: str, port: int, username: str = None, password: str = None):
        self._conn = None
        self._device = {}
        self.device_type = device_type
        self.ip = ip
        self.port = port
        # only set username and password if both are provided
        if username and password:
            self.username = username
            self.password = password

    def __repr__(self) -> str:
        """
        :return: representation of the Connector instance showing all device parameters
        """
        args = ", ".join([f"{arg}={self.device[arg]}" for arg in self.device])
        return f"Connector({args})"

    def __str__(self) -> str:
        return f"{self.device_type} -> {self.ip}:{self.port}"

    @property
    def device_type(self) -> str:
        return self._device["device_type"]

    @device_type.setter
    def device_type(self, device_type: str) -> None:
        """
        Validates and sets the device type for the device
        :param device_type: is the device type as a string
        :return: is None
        :raise TypeError: if the device type is not a string
        :raise ValueError: if the device type does not end with '_telnet'
        """
        # check that the device type is a string
        if not isinstance(device_type, str):
            raise TypeError("TYPE_MUST_BE_A_STRING")
        # check that type ends with _telnet to ensure telnet device connection
        if not device_type.endswith("_telnet"):
            raise ValueError("TYPE_MUST_END_WITH_:'_telnet'")
        self._device["device_type"] = device_type

    @property
    def ip(self) -> str:
        return self._device["ip"]

    @ip.setter
    def ip(self, ip: str) -> None:
        """
        Validates and sets the IP address for the device
        :param ip: is the IP address as a string in the format 'x.x.x.x' where x is between 0 and 255 or 'localhost'
        :return: is None if the IP address is valid
        :raise ValueError: if the IP address is not valid
        """
        if isinstance(ip, str):
            # the pattern matches valid IPv4 addresses and
            # 'localhost', theses are seen as valid input for telnet connections
            if not re.match(r'^(((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$|localhost)',
                            ip):
                raise ValueError(f'INVALID_IP_ADDRESS_FORMAT:{ip}')
            if ip != 'localhost':
                # further check each octet is between 0 and 255
                octets = ip.split('.')
                # this should always be 4 due to the regex match above
                for octet in octets:
                    if not 0 <= int(octet) <= 255:
                        raise ValueError(f'INVALID_IP_ADDRESS_OCTET_RANGE:{ip}')
                # check for special IP addresses that are not allowed (unspecified, multicast, general broadcast)
                if ip == '0.0.0.0' or (224 <= int(ip.split('.')[0]) <= 239) or ip == '255.255.255.255':
                    raise ValueError(f'INVALID_IP_ADDRESS:{ip}')
            self._device["ip"] = ip
            return
        # raise error if ip is not a string, which it should always be for working with netmiko
        raise ValueError(f'INVALID_IP_ADDRESS_TYPE:{type(ip)}')

    @property
    def port(self) -> int:
        return self._device["port"]

    @port.setter
    def port(self, port: int) -> None:
        """
        Validates and sets the port number for the device
        :param port: is the port number as an integer between 0 and 65535
        :return: is None if the port number is valid
        :raise ValueError: if the port number is not valid
        """
        if not isinstance(port, int):
            raise ValueError(f'INVALID_PORT_FORMAT:{type(port)}')
        # valid port range is 0-65535
        if port < 0 or port > 65535:
            raise ValueError(f'PORT_OUT_OF_RANGE:{port}')
        self._device["port"] = port

    @property
    def username(self) -> str:
        return self._device["username"]

    @username.setter
    def username(self, username: str) -> None:
        """
        Sets the username for the device after validating it
        0-64 alphanumeric characters and special characters . _ - @ + $ ~ ! % : / \
        :param username: is the username as a string
        :return: is None
        :raise TypeError: if the username is not a string
        :raise ValueError: if the username contains invalid characters or exceeds length limits
        """
        if not isinstance(username, str):
            raise TypeError(f'INVALID_USERNAME_TYPE:{type(username)}')

        # Regex allows alphanumeric characters and special characters . _ - @ + $ ~ ! % : / \ and a length of 0-64
        username_pattern = r'^[A-Za-z0-9._\-@+$~!%:/\\]{0,64}$'
        if username and re.fullmatch(username_pattern, username) is not None:
            self._device["username"] = username

        elif username is not None:
            raise ValueError(f'INVALID_USERNAME_OR_LENGTH:{username}')

    @property
    def password(self) -> str:
        return self._device["password"]

    @password.setter
    def password(self, pwd: str) -> None:
        """
        Sets the password for the device
        :param pwd: is the password as a string
        :return: is None
        :raise TypeError: if the password is not a string
        :raise ValueError: if the password contains invalid characters or exceeds length limits
        """
        if not isinstance(pwd, str):
            raise TypeError(f'INVALID_PASSWORD_TYPE:{type(pwd)}')

        # Password can be any printable ASCII character, length 0-128
        if not re.match(r'^[\x20-\x7E]{0,128}$', pwd):
            raise ValueError(f'INVALID_PASSWORD_OR_LENGTH:LENGTH:{len(pwd)}|pwd{pwd}')

        self._device["password"] = pwd

    @property
    def device(self) -> dict:
        return self._device

    @property
    def conn(self):
        return self._conn

    def connect(self) -> bool:
        """
        Establishes a telnet connection to the device specified in the instance variables
        :returns: True if connection established successfully, False otherwise
        """
        # Prevent multiple connections
        if self._conn is not None:
            raise RuntimeError(f'CANNOT_ESTABLISH_MULTIPLE_CONNECTIONS_TO_DEVICE_AT:{self.ip}:{self.port}')
        # Establish connection
        try:
            self._conn = ConnectHandler(**self.device)
            return True
        except Exception:
            return False

    def send_command_with_response(self, command: str) -> Tuple[bool, str]:
        """
        Sends a command to the connected device and returns a tuple indicating success and the output in
        :param command: is the command string to send to the device
        :return: (success: bool, output: str)
        """
        output = self._conn.send_command(command)
        # Check for invalid output
        if output.endswith("% Invalid input detected at '^' marker."):
            return False, output
        return True, output

    def send_command(self, command: str, expected_str: str = None) -> bool:
        """
        Sends a command to the connected device and returns True if the parameter expected_str is found at the end of
        the output, False otherwise
        :param command: is the command string to send to the device
        :param expected_str: is the expected string to be found at the end of the output
        :return: is a boolean indicating if the expected string was found
        """
        # ensure connection is established
        if self._conn is None:
            raise RuntimeError("NO_CONNECTION_ESTABLISHED:connect()_NEEDS_TO_BE_CALLED_FIRST.")

        # capture the output to check for errors
        output = self._conn.send_command(command, expect_string=expected_str)
        if output.endswith("% Invalid input detected at '^' marker."):
            return False
        return True

    def send_command_list(self, commands: List[str]) -> str:
        """
        Sends a list of commands to the connected device and returns the combined output as a string
        :param commands: is a list of command strings to send to the device
        :return: is a string containing the combined output of all commands
        """
        output = ""
        for comm in commands:
            # use send_command_with_response to capture output and check for errors
            response = self.send_command_with_response(comm)
            # if command failed, raise error even if other commands were successful before
            if not response[0]:
                raise RuntimeError(f"COMMAND_FAILED:\n{comm}\n{response[1]}")
            output += response[1] + "\n"
        return output

    def get_exec_mode(self) -> ExecMode:
        """
        Determines the current execution mode of the connected device based on the command prompt
        :return: is an ExecMode enumeration value containing the current execution mode
        """
        prompt = self.conn.find_prompt()
        if re.match(r".+>", prompt):
            return ExecMode.USER_EXEC
        if re.match(r".+\)#", prompt):
            return ExecMode.GLOBAL_EXEC
        return ExecMode.PRIVILEGED_EXEC
