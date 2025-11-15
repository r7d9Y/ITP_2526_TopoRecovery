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
logger = logging.getLogger(__name__)
from datetime import datetime

class ConfigReader:
    """
    Reads the configuration file and connects to specified devices in settings.json.
    It gets their configs and writes them to specified location.
    """
    def __init__(self) -> None:
        dest_path = Path(".\\raw_output")
        if not dest_path.exists():
            raise FileNotFoundError("'raw_output' directory does not exist in TopoRecovery")

        self._commands = None
        self._devices = None
        self._dest_path = dest_path

    def read_settings(self, src: str = "./settings.json") -> None:
        """
        Reads settings from given json file
        :param src: Path of settings json file
        :return:
        """
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.setting_syntax_checker(data)
            self._devices = data["devices"]
            self._commands = data["commands"]
            print(data)




    def setting_syntax_checker(self, data: str) -> None:
        """
        Checks the syntax of the ./settings.json file.
        Raises Exception if syntax checks fails
        :raises TypeError if keys or the values are not as defined
        :raises KeyError if specified keys are missing
        :param data: settings.json read as string
        :return: None
        """
        if "devices" not in data:
            raise KeyError("No devices defined in ./settings.json")
        if "commands" not in data:
            raise KeyError("No commands defined in ./settings.json")
        if not isinstance(data, dict):
            raise TypeError(f"data must be of type dict in ./settings.json. Current: {type(data)}")
        devices = data["devices"]
        if not isinstance(devices, dict):
            raise TypeError(f"'devices' must be of type dict in ./settings.json. Current: {type(devices)}")
        commands = data["commands"]
        if not isinstance(commands, dict):
            raise TypeError(f"'commands' must be of type dict in ./settings.json. Current: {type(commands)}")

        for ip in devices:
            #IP-Adresse syntax checker
            if not isinstance(ip, str):
                raise TypeError(f"IP-Address key mus be of type str in ./settings.json. Current: {type(ip)}")
            if not isinstance(devices[ip], dict):
                raise TypeError(f"IP-Address value must be of type dict in ./settings.json. Current: {type(ip)}")

            for port in devices[ip]:
                #Port syntax checker
                if not isinstance(port, str):
                    raise TypeError(f"Port key must be of type dict in ./settings.json. Current: {type(port)}")
                if not isinstance(devices[ip][port], dict):
                    raise TypeError(f"Port value must be of type dict in ./settings.json. Current: {type(port)}")
                props = devices[ip][port]
                #device_type syntax checker
                if "device_type" not in props:
                    raise KeyError("No device_type defined in ./settings.json")
                if not isinstance(props["device_type"], str):
                    raise TypeError("'device_type' must be of type str in ./settings.json")
                if not props["device_type"] in ['switch', 'router']:
                    raise Exception(f"Device type '{props["device_type"]}' is not supported")
                #device_ios syntax checker
                if "device_ios" not in props:
                    raise KeyError("No device_ios defined in ./settings.json")
                if not isinstance(props["device_ios"], str):
                    raise TypeError("'device_ios' must be of type str in ./settings.json")
                #username syntax checker
                if "username" not in props:
                    raise KeyError("No username defined in ./settings.json, if not wanted, give it the value: None")
                if not isinstance(props["username"], str):
                    raise TypeError("'username' must be of type str in ./settings.json")
                #password syntax checker
                if "password" not in props:
                    raise KeyError("No password defined in ./settings.json, if not wanted, give it the value: None")
                if not isinstance(props["password"], str):
                    raise TypeError("'password' must be of type str in ./settings.json")

        if "router" not in commands:
            raise KeyError("Router Commands not found in ./settings.json")
        if "switch" not in commands:
            raise KeyError("Switch Commands not found in ./settings.json")
        for device_commands in commands:
            device_section = commands[device_commands]
            #section syntax checker
            for section in device_section:
                if not isinstance(device_section[section], list):
                    raise TypeError(f"section value must be of type list in ./settings.json")

                #command syntax checker
                for command in device_section[section]:
                    if not isinstance(command, str):
                        raise TypeError(f"command must be of type str in ./settings.json")

    def connect_to_devices(self) -> None:
        """
        Connects to devices specified in settings.json file.
        Writes the output to the destination path specified in creating of the object.
        :return: None
        """
        for ip in self._devices:
            for port in self._devices[ip]:
                prop = self._devices[ip][port]
                try:
                    connection = connector.Connector(prop["device_ios"], ip, port, prop["username"], prop["password"])
                except Exception as e:
                    logging.warning(f"WARNING_SKIPPED_DEVICE")
                    #TODO logging: skipped x.x.x.x device
                    continue

                connection.connect()
                prompt = connection.conn.find_prompt()
                t = datetime.now()
                for section in self._commands[prop["device_type"]]:
                    section_responds = ""
                    for command in self._commands[prop["device_type"]][section]:
                        resp = connection.send_command_with_response(command, expected_str=r'#', read_timeout=90)
                        if not resp[0]:
                            raise ArithmeticError("COMMAND_ERROR")
                        section_responds += resp[1].rstrip()[:-(len(prompt))]
                    self.write_to_dest(f"{ip}_{port}-{t.year}_{t.month}_{t.day}-{t.hour}_{t.minute}_{t.second}_raw_config.txt", section_responds, section)

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

c = ConfigReader()
c.read_settings()
c.connect_to_devices()