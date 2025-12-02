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

    def __init__(self, conf_file: str, device_type: str, ip: str, port: int, username: str = None,
                 password: str = None):
        self.cmds = []
        with open(conf_file, "r", encoding="utf-8") as f:
            self.cmds = f.readlines()
        self.conn = connector.Connector(device_type, ip, port, username, password)

    def send_cmds(self):
        self.conn.connect()
        for cmd in self.cmds:
            r = self.conn.send_command_with_response(cmd)
            if not r[0]:
                logger.warning(f"WARNING_COMMAND_FAILED: {r[1]}")