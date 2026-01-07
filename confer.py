#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import logging

import connector

logger = logging.getLogger(__name__)


class Confer:
    """
    Represents a class for managing device connections and sending commands, based on a
    configuration file.

    This class is designed to simplify the process of connecting to network devices,
    loading a list of commands from a configuration file, and executing them sequentially. It
    abstracts away the underlying connection details, providing an easy-to-use interface for
    working with various device types.

    Attributes:
    cmds (list of str): List of commands read from the configuration file.
    conn (connector.Connector): Connection object initialized with provided device information.

    Methods:
    __init__(conf_file: str, device_type: str, ip: str, port: int, username: str = None,
    password: str = None): Initializes the object with configuration and device connection
    setup.
    send_cmds(): Connects to the device and sends commands sequentially.
    """

    def __init__(self, conf_file: str, device_type: str, ip: str, port: int, username: str = None,
                 password: str = None, secret: str = None):
        """
        Initialize the class with necessary configuration for connecting to a device
        and loading command configurations.

        :param conf_file: Path to the configuration file containing commands
        :param device_type: Type of the device (e.g., router, switch)
        :param ip: IP address of the device
        :param port: Port number for the connection
        :param username: Username for authentication (optional)
        :param password: Password for authentication (optional)
        :param secret: Secret for Privileged Exec Mode authentication (optional)
        """
        self.cmds = []
        with open(conf_file, "r", encoding="utf-8") as f:
            self.cmds = f.readlines()
        self.conn = connector.Connector(device_type, ip, port, username, password, secret)

    def send_cmds(self):
        """
        Executes a series of commands by establishing a connection and sending
        each command sequentially. If a command execution fails, logs a warning and prints it to the terminal.
        :return: None
        """
        self.conn.connect()
        self.conn.go_to_glob_exec_mode()
        self.conn.send_command_with_response("no logging console", expected_str=r"\(config[^\)]*\)#")
        for cmd in self.cmds:
            r = self.conn.send_command_with_response(cmd, expected_str=r"\(config[^\)]*\)#")
            if not r[0]:
                logger.warning(f"WARNING_COMMAND_FAILED_WHILE_UPLOADING: {r[1]}")
                colorRed = "\033[31m"
                colorReset = "\033[0m"
                print(f"{colorRed}WARNING_COMMAND_FAILED_WHILE_UPLOADING: {r[1]}{colorReset}")
        self.conn.go_to_glob_exec_mode()
        self.conn.send_command_with_response("logging console", expected_str=r"\(config[^\)]*\)#")
