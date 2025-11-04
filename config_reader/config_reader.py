from connector import connector
class Config_reader:
    def __init__(self, device_type: str, ip: str, port: int, username: str = None,
                 password: str = None, dest_path = "../raw_output.txt") -> None:
        self._connection = connector(device_type, ip, port, username, password)
        self._dest_path = dest_path

    def write_to_dest(self, config: str, section: str) -> bool:
        with open(self._dest_path, "a") as dest:
            dest.write(f"** start {section} **\n")
            dest.write(config)
            dest.write(f"\n** end {section} **\n")

