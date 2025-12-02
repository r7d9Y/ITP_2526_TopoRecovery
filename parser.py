#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import logging
import re

logger = logging.getLogger(__name__)


def parse(input_filename: str, ip: str, port: int):
    """
    :param input_filename: File mit der Konfiguration die geparsed wird
    :param ip: IP Adresse des ausgelesen Geräts
    :param port: der Port mit dem man auf das Gerät kommt

    Der Code der Methode "parse", parsed ein raw Output-File in eine Konfiguration, die man genau so wieder ein zu eins auf ein Gerät rausspielen kann.
    In dem File welches über input_filename übergeben wird steht beim Router und ein "show interface brief".
    Beim Switch steht ergänzend zur running-config des ausgelesenen Geräts noch der Output von "show vlan brief", "show vtp status", "show vtp password" und "show ip interface brief".
    Für die fertige Konfiguration wird ein Output-File erstellt, in der die Konfiguration steht.

    """

    with open(input_filename, "r", encoding="utf-8") as f:
        zeilen = f.readlines()  # Liste mit alle Zeilen
    with open("matchlist", "r", encoding="utf-8") as f:
        std = f.readlines()
    with open(re.sub("raw_","",input_filename), "w") as f:
        # -----------VLAN------------

        # VLAN-Nummern + Name ermitteln
        vlan_start_index = 0
        for index, line in enumerate(zeilen):  # enumerate gibt Index und Zeile
            if re.search(r"\*\* start vlan \*\*", line):
                vlan_start_index = index
                break

        # Code für das Bereinigen der running-config ...
        end_run = vlan_start_index - 2
        run = zeilen[1:end_run]
        run = re.sub(r"\n{2,}", "\n\n", re.sub(r"(((line)|(interface)|(router)).*)", r"\n\1",
                                               re.sub(r"(([\n\r])\s*!.*)+", "\n", "".join(run), flags=re.M),
                                               flags=re.M), flags=re.M)
        for i in std:
            run = re.sub("^\\s*" + i + "+", "\n", run, flags=re.M)
        del std

        # Hinzufügen von no shuts
        intc = "".join(zeilen[zeilen.index("** start interface **\n") + 1:])
        ints = re.findall("interface .*", run)
        for i in ints:
            r = ""
            iname = re.sub(r"interface (.*)", r"\1", i)
            if intc[intc.index(iname) + 50] == "u":
                r = i + "\nno shutdown\n"
            if not re.search(i+r"\n\n", run):
                r=i+"\n"
            run = re.sub(i + "\n", r, run)

        f.write(run)
        logger.info(f"SUCCESS_RUN_CONFIG_PARSED_SUCCESSFUL", extra={'ip': ip, 'port': port})

        # ------

        found_vlan_config = False
        # VLAN-Konfig erstellen und in das Output-File schreiben
        for vlan_konfig_zeile in zeilen[vlan_start_index:]:
            if not vlan_konfig_zeile[0].isdigit() or vlan_konfig_zeile[0].isdigit() and int(
                    vlan_konfig_zeile[:4].strip()) < 1001:
                if vlan_konfig_zeile[0].isdigit() and int(vlan_konfig_zeile[:4].strip()) != 1:
                    parts = vlan_konfig_zeile.split()  # Zeile an Leerzeichen teilen
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

        # Start-Lese-Index ermitteln
        vtp_start_index = 0
        for index, line in enumerate(zeilen):
            if re.search(r"\*\* start vtp \*\*", line):
                vtp_start_index = index + 1
                break

        write_konfig = False  # Es soll nur etwas rausgeschrieben werden, wenn auch eine Konfig existiert
        vtp_commands_to_write = []  # Liste mit allen Commands, die in das Output-File geschrieben werden wenn die Variable 'write_konfig' True ist

        # VTP-Konfig parsen
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
        if write_konfig:  # wenn die Variable auf True gesetzt wurde, werden alle Elemente aus der Liste in das Output-File geschrieben
            f.writelines(vtp_commands_to_write)

        logger.info(f"SUCCESS_OUTPUT_FILE_SAVED_SUCCESSFUL", extra={'ip': ip, 'port': port})