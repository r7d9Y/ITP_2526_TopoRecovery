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
        for ip in self._devices:
            for port in self._devices[ip]:
                prop = self._devices[ip][port]
                connection = connector.Connector(prop["device_ios"], ip, port, prop["username"], prop["password"])
                connection.connect()
                #TODO go into privilaged mode
                for section in self._commands[prop["device_type"]]:
                    section_responds = ""
                    for command in self._commands[prop["device_type"]][section]:
                        print(connection.conn)
                        print(connection)
                        prompt = connection.conn.find_prompt()
                        resp = connection.send_command_with_response(command, expected_str=r'#', read_timeout=90)[:-len(prompt)]
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