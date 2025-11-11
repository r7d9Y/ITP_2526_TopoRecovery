from connector import connector
import json

class ConfigReader:
    """
    Reads the configuration file and connects to specified devices in settings.json.
    It gets their configs and writes them to specified location.
    """
    def __init__(self, dest_path: str = "../raw_output.txt") -> None:
        self._commands = None
        self._devices = None
        self._dest_path = dest_path

    def read_settings(self, src: str = "../settings/settings.json") -> None:
        """
        Reads settings from given json file
        :param src: Path of settings json file
        :return:
        """
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._devices = data["devices"]
            self._commands = data["commands"]
            print(data)


    def connect_to_devices(self):
        """
        Connects to devices specified in settings.json file.
        Writes the output to the destination path specified in creating of the object.
        :return:
        """
        for ip in self._devices:
            for port in self._devices[ip]:
                prop = self._devices[ip][port]
                connection = connector.Connector(prop["device_ios"], ip, port, prop["username"], prop["password"])
                connection.connect()
                prompt = connection.conn.find_prompt()

                for section in self._commands[prop["device_type"]]:
                    section_responds = ""
                    for command in self._commands[prop["device_type"]][section]:
                        resp = connection.send_command_with_response(command, expected_str=r'#', read_timeout=90)
                        if not resp[0]:
                            raise ArithmeticError("COMMAND_ERROR")
                        section_responds += resp[1].rstrip()[:-(len(prompt))]
                    self.write_to_dest(section_responds, section)

    def write_to_dest(self, config: str, section: str) -> bool:
        """
        Appends given string to specified destination path and surrounds the string with the section string, z.B.:\n
        \*** run \***\n
        hostname R1\n
        \*** run \***\n
        :param config: string to be appended to destination path
        :param section: string to mark beginning and end of section
        :return:
        """
        with open(self._dest_path, "a") as dest:
            dest.write(f"** start {section} **\n")
            dest.write(config)
            dest.write(f"\n** end {section} **\n")

c = ConfigReader()
c.read_settings()
c.connect_to_devices()