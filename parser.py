#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def parse(input_filename: Path, ip: str, port: int):
    """
    :param input_filename: File containing the configuration that will be parsed
    :param ip: IP address of the device that was read
    :param port: The port used to access the device

    The code of the "parse" method parses a raw output file into a configuration that can be uploaded back onto a device exactly as it is

    In the file passed via the parameter input_filename, the router contains a "show interface brief"
    For the switch, in addition to the running configuration of the device, the output of "show vlan brief", "show vtp status", "show vtp password", and "show ip interface brief" is also included
    For the final configuration, an output file is created that contains the resulting configuration

    """

    with open(input_filename, "r", encoding="utf-8") as f:
        zeilen = f.readlines()  # list with all lines of the file
    with open("settings/matchlist", "r", encoding="utf-8") as f:
        std = f.readlines()
    with open(re.sub("raw_", "", str(input_filename)), "w") as f:
        # -----------VLAN------------

        # gets vlan numbers and names
        vlan_start_index = 0
        for index, line in enumerate(zeilen):  # enumerate returns both index and line
            if re.search(r"\*\* start vlan \*\*", line):
                vlan_start_index = index
                break

        # Code for cleaning up the running-config ...
        end_run = zeilen.index("** end running **\n")
        run = zeilen[1:end_run]
        run = re.sub(r"\n{2,}", "\n\n", re.sub(r"^(((line)|(interface)|(router)).*)", r"\n\1",
                                               re.sub(r"(([\n\r])\s*!.*)+", "\n", "".join(run), flags=re.M),
                                               flags=re.M), flags=re.M)
        for i in std:
            run = re.sub("^\\s*" + i + "+", "\n", run, flags=re.M)
        del std

        # Hinzufügen von no shuts
        intc = "".join(zeilen[zeilen.index("** start interface **\n") + 1:])
        ints = re.findall(r"^interface .*", run,flags=re.M)
        for i in ints:
            r = ""
            iname = re.sub(r"^interface (.*)", r"\1", i,flags=re.M)
            if intc[intc.index(iname) + 50] == "u":
                r = i + "\nno shutdown\n"
            elif not re.search(i + r"\n\n", run):
                r = i + "\n"
            run = re.sub(i + "\n", r, run)

        f.write(run)
        logger.info(f"SUCCESS_RUN_CONFIG_PARSED_SUCCESSFUL", extra={'ip': ip, 'port': port})

        # ------

        found_vlan_config = False
        # creates the vlan configuration part and writes it to the output file
        for vlan_konfig_zeile in zeilen[vlan_start_index:]:
            if not vlan_konfig_zeile[0].isdigit() or vlan_konfig_zeile[0].isdigit() and int(
                    vlan_konfig_zeile[:4].strip()) < 1001:
                if vlan_konfig_zeile[0].isdigit() and int(vlan_konfig_zeile[:4].strip()) != 1:
                    parts = vlan_konfig_zeile.split()  # split line at whitespace
                    vlan_nummer = parts[0]
                    vlan_name = parts[1]
                    f.write(f"vlan {vlan_nummer} \nname {vlan_name}\n")
                    found_vlan_config = True
            else:
                break
        if not found_vlan_config:
            logger.warning("WARNING_NO_VLAN_CONFIG_RECEIVED", extra={'ip': ip, 'port': port})
        else:
            logger.info(f"SUCCESS_VLAN_CONFIG_PARSED_SUCCESSFUL", extra={'ip': ip, 'port': port})

        # -----------VTP------------

        # gets the start index of the vtp configuration
        vtp_start_index = 0
        for index, line in enumerate(zeilen):
            if re.search(r"\*\* start vtp \*\*", line):
                vtp_start_index = index + 1
                break

        write_konfig = False  # only write output if a configuration exists
        vtp_commands_to_write = []  # list of all commands to write to the output file if 'write_konfig' is True

        # parse the vtp configuration part
        for vtp_konfig_zeile in zeilen[vtp_start_index:]:
            if ":" in vtp_konfig_zeile:
                parts = vtp_konfig_zeile.split(":", 1)

                if parts[0].strip() == "VTP Operating Mode":
                    vtp_commands_to_write.append(f"vtp mode {parts[1].strip()}\n")
                elif parts[0].strip() == "VTP version running":
                    vtp_commands_to_write.append(f"\nvtp version {parts[1].strip()}\n")
                elif parts[0].strip() == "VTP Domain Name":
                    vtp_commands_to_write.append(f"vtp domain {parts[1].strip()}\n")
                elif parts[0].strip() == "VTP Password":
                    vtp_commands_to_write.append(f"vtp password {parts[1].strip()}\n")
                elif parts[0].strip() == "Configuration Revision":
                    if int(parts[1].strip()) > 0:
                        write_konfig = True
                        logger.info(f"SUCCESS_VTP_CONFIG_PARSED_SUCCESSFUL", extra={'ip': ip, 'port': port})
                    else:
                        logger.warning(f"WARNING_NO_VTP_CONFIG_RECEIVED", extra={'ip': ip, 'port': port})
        if write_konfig:  # if the variable is set to True, all elements from the list are written to the output file
            f.writelines(vtp_commands_to_write)

        logger.info(f"SUCCESS_OUTPUT_FILE_SAVED_SUCCESSFUL", extra={'ip': ip, 'port': port})