import re
from netmiko import ConnectHandler

class Connector:
    def __init__(self, device_type, ip, port, username = None, password = None):
        self._device = {}
        self.device_type = device_type
        self.ip = ip
        self.port = port
        if username and password:
            self.username = username
            self.password = password


    def __repr__(self):
        return f"Connector(ip={self.ip}, port={self.port})"

    def __str__(self):
        string = ".".join([str(self.ip >> (8 * (3 - i)) & 255) for i in range(4)])
        return f"{string}:{str(self.port)}"

    @property
    def device_type(self):
        return self._device["device_type"]

    @device_type.setter
    def device_type(self, type):
        if not isinstance(type, str):
            raise TypeError("Type must be a string")
        if not type.endswith("_telnet"):
            raise ValueError("Type must end with '_telnet'")
        self._device["device_type"] = type

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, add):
        if isinstance(add, str):
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', add):
                raise ValueError('Invalid IP address format')
            ip = 0
            for i, seg in enumerate(add.split('.')):
                if not 0 <= int(seg) <= 255:
                    raise ValueError('Invalid IP address ##')
                ip = int(seg) << (8 * (3 - i)) | ip
            self._ip = ip
            return
        if isinstance(add, int):
            if not 0 <= add <= 2**32:
                raise ValueError('Invalid IP address')
            self._ip = add
            return
        raise ValueError('Invalid IP address format')

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        if not isinstance(port, int):
            raise ValueError('Invalid port format')
        self._port = port

    @property
    def username(self):
        return self._device["username"]

    @username.setter
    def username(self, username):
        if not isinstance(username, str):
            raise TypeError('Invalid username type')
        self._device["username"] = username

    @property
    def password(self):
        return self._device["password"]

    @password.setter
    def password(self, pwd):
        if not isinstance(pwd, str):
            raise TypeError('Invalid username type')
        self._device["password"] = pwd

    def connect(self):
        pass


if __name__ == '__main__':
    c = Connector('127.0.0.1', 80)
    print(str(c))