#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

from pathlib import Path

import connector
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigReader:
    """
    Reads the configuration file and connects to specified devices in reader_settings.json.
    It gets their configs and writes them to specified location.
    """

    def __init__(self, dest_path: Path = Path(".\\raw_output"), setting_path: Path = Path(
        "settings/reader_settings.json")) -> None:
        dest_path.mkdir(exist_ok=True)
        self._dest_path = dest_path
        self._setting_path = setting_path
        self._commands = None
        self._devices = None
        self._dest_path = dest_path

    def read_settings(self) -> None:
        """
        Reads settings from given json file
        :return: None
        """
        src = self._setting_path
        if not src.exists():
            raise FileNotFoundError(f"FILE_NOT_FOUND: reader_settings.json does not exist in {src.parent}")
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.setting_syntax_checker(data)
            self._devices = data["devices"]
            self._commands = data["commands"]

    def setting_syntax_checker(self, data: str) -> None:
        """
        Checks the syntax of the ./reader_settings.json file.
        Raises Exception if syntax checks fails
        :raises TypeError if keys or the values are not as defined
        :raises KeyError if specified keys are missing
        :param data: reader_settings.json read as string
        :return: None
        """
        dPath = self._setting_path
        if "devices" not in data:
            raise KeyError(f"KEY_ERROR: No devices defined in {dPath}")
        if "commands" not in data:
            raise KeyError(f"KEY_ERROR:No commands defined in {dPath}")
        if not isinstance(data, dict):
            raise TypeError(f"TYPE_ERROR: data must be of type dict in {dPath}. Current: {type(data)}")
        devices = data["devices"]
        if not isinstance(devices, dict):
            raise TypeError(f"TYPE_ERROR: 'devices' must be of type dict in {dPath}. Current: {type(devices)}")
        commands = data["commands"]
        if not isinstance(commands, dict):
            raise TypeError(f"TYPE_ERROR: 'commands' must be of type dict in {dPath}. Current: {type(commands)}")

        for ip in devices:
            # IP-Adresse syntax checker
            if not isinstance(ip, str):
                raise TypeError(f"TYPE_ERROR: IP-Address key mus be of type str in {dPath}. Current: {type(ip)}")
            if not isinstance(devices[ip], dict):
                raise TypeError(f"TYPE_ERROR: IP-Address value must be of type dict in {dPath}. Current: {type(ip)}")

            for port in devices[ip]:
                # Port syntax checker
                if not isinstance(port, str):
                    raise TypeError(f"TYPE_ERROR: Port key must be of type dict in {dPath}. Current: {type(port)}")
                if not isinstance(devices[ip][port], dict):
                    raise TypeError(f"TYPE_ERROR: Port value must be of type dict in {dPath}. Current: {type(port)}")
                props = devices[ip][port]
                # device_type syntax checker
                if "device_type" not in props:
                    raise KeyError(f"KEY_ERROR: No device_type defined in {dPath}")
                if not isinstance(props["device_type"], str):
                    raise TypeError(f"TYPE_ERROR: 'device_type' must be of type str in {dPath}")
                if not props["device_type"] in ['switch', 'router']:
                    raise ValueError(f"VALUE_ERROR: Device type '{props["device_type"]}' is not supported")
                # device_ios syntax checker
                if "device_ios" not in props:
                    raise KeyError(f"KEY_ERROR: No device_ios defined in {dPath}")
                if not isinstance(props["device_ios"], str):
                    raise TypeError(f"TYPE_ERROR: 'device_ios' must be of type str in {dPath}")
                # username syntax checker
                if "username" not in props:
                    raise KeyError(f"KEY_ERROR: No username defined in {dPath}, if not wanted, give it the value: None")
                if not isinstance(props["username"], str):
                    raise TypeError(f"TYPE_ERROR: 'username' must be of type str in {dPath}")
                # password syntax checker
                if "password" not in props:
                    raise KeyError(f"KEY_ERROR: No password defined in {dPath}, if not wanted, give it the value: None")
                if not isinstance(props["password"], str):
                    raise TypeError(f"TYPE_ERROR: 'password' must be of type str in {dPath}")

        if "router" not in commands:
            raise KeyError(f"KEY_ERROR: Router Commands not found in {dPath}")
        if "switch" not in commands:
            raise KeyError(f"KEY_ERROR: Switch Commands not found in {dPath}")
        for device_commands in commands:
            device_section = commands[device_commands]
            # section syntax checker
            for section in device_section:
                if not isinstance(device_section[section], list):
                    raise TypeError(f"TYPE_ERROR: section value must be of type list in {dPath}")

                # command syntax checker
                for command in device_section[section]:
                    if not isinstance(command, str):
                        raise TypeError(f"TYPE_ERROR: command must be of type str in {dPath}")

    def get_logging_str(self, ip, port):
        """
        gibt einen string zurück, der ein logging format entspricht:

        2025:11:25_12:46:23_172.16.0.117:5018

        :param ip:
        :param port:
        :return:
        """
        # 2025:11:25_12:46:23_172.16.0.117:5018
        t = datetime.now()
        return f"{t.year}:{t.month}:{t.day}_{t.hour}:{t.minute}:{t.second}_{ip}:{port}"

    def connect_to_devices(self) -> None:
        """
        Connects to devices specified in reader_settings.json file.
        Writes the output to the destination path specified in creating of the object.
        :return: None
        """
        for ip in self._devices:
            for port in self._devices[ip]:
                prop = self._devices[ip][port]
                try:
                    connection = connector.Connector(prop["device_ios"], ip, port, prop["username"], prop["password"])

                    connection.connect()
                    prompt = connection.conn.find_prompt()
                    t = datetime.now()
                    for section in self._commands[prop["device_type"]]:
                        section_responds = ""
                        for command in self._commands[prop["device_type"]][section]:
                            resp = connection.send_command_with_response(command, expected_str=r'#', read_timeout=90)
                            if not resp[0]:
                                raise RuntimeError("COMMAND_ERROR")
                            section_responds += resp[1].rstrip()[:-(len(prompt))]
                        self.write_to_dest(
                            f"{ip}_{port}-{t.year}_{t.month}_{t.day}-{t.hour}_{t.minute}_{t.second}_raw_config.txt",
                            section_responds, section)
                except Exception as e:
                    logger.error(f"{e}", extra={'ip': ip, 'port': port})
                    logger.warning(f"WARNING_SKIPPED_DEVICE", extra={'ip': ip, 'port': port})
                    colorRed = "\033[31m"
                    colorReset = "\033[0m"
                    print(f"{colorRed}{self.get_logging_str(ip, port)}--{e}{colorReset}")
                    print(f"{colorRed}{self.get_logging_str(ip, port)}--WARNING_SKIPPED_DEVICE{colorReset}")
                    continue

    def write_to_dest(self, file_name: str, config: str, section: str) -> bool:
        """
        Appends given string to specified destination path and surrounds the string with the section string, z.B.:

        *** *** *** run *** *** ***

        hostname R1

        *** *** *** run *** *** ***
        :param file_name: name of the file to write to
        :param config: string to be appended to destination path
        :param section: string to mark beginning and end of section
        :return:
        """
        with open(self._dest_path.joinpath(Path(file_name)), "a") as dest:
            dest.write(f"** start {section} **\n")
            dest.write(config)
            dest.write(f"\n** end {section} **\n")

    def execute(self):
        """
        executes the basic commands for a functional config_reader.
        It checks the setting syntax and throws an Error if it is wrong.
        It then calls to read the setting file and connect to the specified devices and gets their configs.
        :return:
        """
        self.read_settings()
        self.connect_to_devices()
