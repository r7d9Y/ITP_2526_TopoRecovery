import re
from typing import Tuple, List

from netmiko import ConnectHandler

class Connector:
    def __init__(self, device_type: str, ip: str, port: int, username: str = None, password: str = None):
        self._device = {}
        self.device_type = device_type
        self.ip = ip
        self.port = port
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
        if not isinstance(type, str):
            raise TypeError("Type must be a string")
        if not type.endswith("_telnet"):
            raise ValueError("Type must end with '_telnet'")
        self._device["device_type"] = type

    @property
    def ip(self) -> str:
        return self._device["ip"]

    @ip.setter
    def ip(self, add: str) -> None:
        if isinstance(add, str):
            # the pattern matches valid IPv4 addresses and
            # 'localhost', theses are seen as valid input for telnet connections
            if not re.match(r'^(((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$|localhost)', add):
                raise ValueError('Invalid IP address format')
            self._device["ip"] = add
            return
        raise ValueError('Invalid IP address format')

    @property
    def port(self) -> int:
        return self._device["port"]

    @port.setter
    def port(self, port: int) -> None:
        if not isinstance(port, int):
            raise ValueError('Invalid port format')
        self._device["port"] = port

    @property
    def username(self) -> str:
        return self._device["username"]

    @username.setter
    def username(self, username: str) -> None:
        if not isinstance(username, str):
            raise TypeError('Invalid username type')
        self._device["username"] = username

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
    def conn(self) -> ConnectHandler:
        return self._conn

    def connect(self) -> ConnectHandler:
        if hasattr(self, "_conn"):
            raise RuntimeError('Cannot connect twice')
        self._conn = ConnectHandler(**self.device)

    def send_command_with_response(self, command: str) -> Tuple[bool, str]:
        output = self._conn.send_command(command)
        if output.endswith("% Invalid input detected at '^' marker."):
            return False, output
        return True, output

    def send_command(self, command: str, expected_str: str = None) -> bool:
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