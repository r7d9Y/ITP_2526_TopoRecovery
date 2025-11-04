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
        args = ", ".join([f"{arg}={self.device[arg]}" for arg in self.device])
        return f"Connector({args})"

    def __str__(self) -> str:
        return f"{self.device_type} -> {self.ip}:{self.port}"

    @property
    def device_type(self) -> str:
        return self._device["device_type"]

    @device_type.setter
    def device_type(self, type: str) -> None:
        # check that the device type is a string
        if not isinstance(type, str):
            raise TypeError("TYPE_MUST_BE_A_STRING")
        # check that type ends with _telnet to ensure telnet device connection
        if not type.endswith("_telnet"):
            raise ValueError("TYPE_MUST_END_WITH_'_telnet'")
        self._device["device_type"] = type

    @property
    def ip(self) -> str:
        return self._device["ip"]

    @ip.setter
    def ip(self, ip: str) -> None:
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
        if not isinstance(port, int):
            raise ValueError(f'INVALID_PORT_FORMAT:{type(port)}')
        if port < 0 or port > 65535:
            raise ValueError(f'PORT_OUT_OF_RANGE:{port}')
        self._device["port"] = port

    @property
    def username(self) -> str:
        return self._device["username"]

    @username.setter
    def username(self, username: str) -> None:
        if not isinstance(username, str):
            raise TypeError(f'INVALID_USERNAME_TYPE:{type(username)}')

        # Regex allows alphanumeric characters and special characters . _ - @ + $ ~ ! % : / \ and a length of 0-64
        pattern = r'^[A-Za-z0-9._\-@+$~!%:/\\]{0,64}$'
        if username and re.fullmatch(pattern, username) is not None:
            self._device["username"] = username
        elif username is not None:
            raise ValueError(f'INVALID_USERNAME_OR_LENGTH:{username}')

    @property
    def password(self) -> str:
        return self._device["password"]

    @password.setter
    def password(self, pwd: str) -> None:
        if not isinstance(pwd, str):
            raise TypeError('Invalid username type')
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
        output = self.conn.send_command(command, expect_string=expected_str)
        if output.endswith("% Invalid input detected at '^' marker."):
            return False
        return True

    def send_command_list(self, commands: List[str]) -> str:
        output = ""
        for comm in commands:
            response = self.send_command_with_response(comm)
            if not response[0]:
                raise RuntimeError(f"Command failed:\n{comm}\n{comm[1]}")
            output += response[1]
        return output

    def get_exec_mode(self) -> str:
        prompt = self.conn.find_prompt()
        if re.match(".+>", prompt):
            return "USER_EXEC"
        if re.match(".+\\)#", prompt):
            return "GLOBAL_EXEC"
        return "PRIVILEGED_EXEC"

    """def go_into_privileged_mode(self, password: str) -> bool:
        mode = self.get_exec_mode()
        if mode == "USER_EXEC":
            self.send_command("enable", r".*")
            return self.send_command(password, r".*")
        if mode == "GLOBAL_EXEC":
            return self.send_command("end", r".*")
        return False"""


if __name__ == '__main__':
    c = Connector('cisco_ios_telnet', '192.168.44.128', 5001, "cisco", "cisco")
    print(repr(c))
    print(str(c))
    c.connect()

    print(c.send_command('show ip int bief'))
    c.get_exec_mode()
    c.go_into_privileged_mode("cisco")