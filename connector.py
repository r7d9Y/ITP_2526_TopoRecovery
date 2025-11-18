#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______
from datetime import datetime
import re
from multiprocessing import AuthenticationError
from re import PatternError
from typing import Tuple, List
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException

import paramiko
import socket
from enum import Enum, auto
import logging

from paramiko.ssh_exception import SSHException

logger = logging.getLogger(__name__)


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
            raise TypeError(f"DEVICE_TYPE_TYPE_ERROR:'device_type' must be a string -> currently {type(device_type)}")
        # check that type ends with _telnet to ensure telnet device connection
        if not device_type.endswith("_telnet"):
            raise ValueError("DEVICE_TYPE_VALUE_ERROR:'device_type' must end with:'_telnet'")
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
                raise ValueError(f'IP_VALUE_ERROR:invalid ip address format: {ip}')
            if ip != 'localhost':
                # further check each octet is between 0 and 255
                octets = ip.split('.')
                # this should always be 4 due to the regex match above
                for octet in octets:
                    if not 0 <= int(octet) <= 255:
                        raise ValueError(f'IP_OCTET_VALUE_ERROR:invalid ip octet range, must be between 0 and 255:{ip}')
                # check for special IP addresses that are not allowed (unspecified, multicast, general broadcast)
                if ip == '0.0.0.0' or (224 <= int(ip.split('.')[0]) <= 239) or ip == '255.255.255.255':
                    raise ValueError(f'INVALID_IP_ADDRESS: {ip} -> not allowd addresses: 0.0.0.0, first octet between 224 '
                                     f'and 239, 255.255.255.255')
            self._device["ip"] = ip
            return
        # raise error if ip is not a string, which it should always be for working with netmiko
        raise TypeError(f"IP_TYPE_ERROR: 'ip' must be a string -> currently: {type(ip)}")

    @property
    def port(self) -> int:
        return self._device["port"]

    @port.setter
    def port(self, port: int) -> None:
        if not isinstance(port, (int, str)) and not (isinstance(port, str) and re.match(r'^(-?\d+)$', port)):
            raise TypeError(f'PORT_TYPE_ERROR:invalid port type -> currently: {type(port)}')
        port = int(port)
        # valid port range is 0-65535
        if port < 0 or port > 65535:
            raise ValueError(f'PORT_VALUE_ERROR: port out of range, must be between 0 and 65535 -> currently: {port}')
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
            raise TypeError(f'USERNAME_TYPE_ERROR: username must be a string -> currently: {type(username)}')

        # Regex allows alphanumeric characters and special characters . _ - @ + $ ~ ! % : / \ and a length of 0-64
        username_pattern = r'^[A-Za-z0-9._\-@+$~!%:/\\]{1,64}$'
        if username and re.fullmatch(username_pattern, username) is not None:
            self._device["username"] = username

        elif username is not None:
            raise PatternError(f'USERNAME_PATTERN_ERROR: invalid username or length (between 0 and 64 Chars), '
                               f'must match: {username_pattern} -> current username: {username}')

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
            raise TypeError(f'PASSWORD_TYPE_ERROR: password type must be a string -> currently:{type(pwd)}')

        # Password can be any printable ASCII character, length 0-128
        pattern = r'^[\x20-\x7E]{0,128}$'
        if not re.match(pattern, pwd):
            raise ValueError(f'PASSWORD_VALUE_ERROR: invalid password or length, must match {pattern}'
                             f' -> currently LENGTH:{len(pwd)}, pwd{pwd}')

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
        :raise RuntimeError: if a connection is already established
        """
        # Prevent multiple connections
        if self._conn is not None:
            raise ConnectionError(f'CONNECTION_ERROR: cannot establish multiple connections to one device, at {self.ip}:{self.port}')
        # Establish connection
        try:
            self._conn = ConnectHandler(**self.device)
        except NetMikoTimeoutException as e:
            # Gerät nicht erreichbar / Timeout
            raise TimeoutError('TIMEOUT_ERROR: device not reachable (Layer 8?)')
        except NetMikoAuthenticationException as e:
            # Falsche Credentials o.ä.
            raise AuthenticationError(f'AUTHENTICATION_ERROR: {e}')
        except paramiko.ssh_exception.SSHException as e:
            raise SSHException(f'SSH_ERROR: {e}')
        except (socket.timeout, socket.error, OSError) as e:
            raise ConnectionError(f'TIMEOUT_ERROR: {e}')
        except Exception as e:
            # Fallback für alles andere
            raise Exception(f'UNKNOWN_ERROR: {e}')




    def send_command_with_response(self, command: str, expected_str: str = None, read_timeout: int = 10) -> Tuple[bool, str]:
        """
        Sends a command to the connected device and returns a tuple indicating success and the output in
        :param expected_str: is the expected string to be found at the end of the output
        :param read_timeout: how long the code waits for a response before an exception is raised time in seconds
        :param command: is the command string to send to the device
        :return: (success: bool, output: str)
        """
        output = self._conn.send_command(command, read_timeout=read_timeout, delay_factor=2, expect_string=expected_str)
        # Check for invalid output
        if output.endswith("% Invalid input detected at '^' marker."):
            return False, output
        return True, output

    def was_command_send_successfully(self, command: str, expected_str: str = None) -> bool:
        """
        Sends a command to the connected device and returns True if the parameter expected_str is found at the end of
        the output, False otherwise
        :param command: is the command string to send to the device
        :param expected_str: is the expected string to be found at the end of the output
        :return: is a boolean indicating if the expected string was found
        :raise RuntimeError: if no connection is established
        """
        # ensure connection is established
        if self._conn is None:
            raise RuntimeError("RUNTIME_ERROR: no current running connection, call connect() to establish connection")

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
        :raise RuntimeError: if any command fails
        """
        output = ""
        for comm in commands:
            # use send_command_with_response to capture output and check for errors
            response = self.send_command_with_response(comm)
            # if command failed, raise error even if other commands were successful before
            if not response[0]:
                raise RuntimeError(f"RUNTIME_ERROR: command failed: \n{comm}\n{response[1]}")
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
