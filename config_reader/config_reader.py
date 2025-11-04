from connector import connector
import json

class ConfigReader:
    def __init__(self, dest_path = "../raw_output.txt") -> None:
        self._commands = None
        self._devices = None
        self._dest_path = dest_path

    def read_settings(self, src ="../settings/settings.json"):
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._devices = data["devices"]
            self._commands = data["commands"]
            print(data)


    def connect_to_devices(self):
        for device in self._devices:
            prop = self._devices[device]
            for port in prop["port"]:
                connection = connector.Connector(prop["device_type"], device, port, prop["username"], prop["password"])
                connection.connect()
                #TODO go into privilaged mode
                for section in self._commands:
                    section_responds = ""
                    for command in self._commands[section]:
                        prompts = self._commands[section]
                        resp = connection.send_command_with_response(command)
                        if not resp[0]:
                            raise ArithmeticError("COMMAND_ERROR")
                        section_responds += resp[1]
                    self.write_to_dest(section_responds, section)

    def write_to_dest(self, config: str, section: str) -> bool:
        with open(self._dest_path, "a") as dest:
            dest.write(f"** start {section} **\n")
            dest.write(config)
            dest.write(f"\n** end {section} **\n")

c = ConfigReader()
c.read_settings()
c.connect_to_devices()