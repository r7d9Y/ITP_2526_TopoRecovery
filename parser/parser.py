#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import re


def parse():
    with open("./raw_output_testdatei.txt", "r", encoding="utf-8") as f:
        zeilen = f.readlines()  # Liste mit alle Zeilen

    with open("output.txt", "w") as f:

        # VLAN-Nummern + Name ermitteln
        vlan_start_index = 0
        for index, line in enumerate(zeilen):  # enumerate gibt Index und Zeile
            if re.search(r"\*\* start vlan \*\*", line):
                vlan_start_index = index
                break

        # Code für das Bereinigen der running-config ...
        end_run = vlan_start_index - 2
        run = zeilen[:end_run]
        run = re.sub(r"\n{2,}", "\n\n", re.sub(r"^ *!.*$", "", "\n".join(run), re.M))

        # VLAN-Konfig parsen
        for vlan_konfig_zeile in zeilen[vlan_start_index:]:
            if not vlan_konfig_zeile[0].isdigit() or vlan_konfig_zeile[0].isdigit() and int(
                    vlan_konfig_zeile[:4].strip()) < 1001:
                if vlan_konfig_zeile[0].isdigit() and int(vlan_konfig_zeile[:4].strip()) != 1:
                    vlan_nummer: str = ""
                    vlan_name: str = ""
                    parts = vlan_konfig_zeile.split()  # Zeile an Leerzeichen teilen
                    vlan_nummer = parts[0]
                    vlan_name = parts[1]
                    f.write(f"vlan {vlan_nummer} \nname {vlan_name}\n")
            else:
                break

        # VTP-Konfig parsen
        vtp_start_index = 0
        for index, line in enumerate(zeilen):
            if re.search(r"\*\* start vtp \*\*", line):
                vtp_start_index = index
                break

        vtp_version = ""
        vtp_mode = ""
        vtp_domain = ""
        vtp_password = ""
        for vtp_konfig_zeile in zeilen[vtp_start_index:]:
            if re.search(r"VTP Operating Mode", vtp_konfig_zeile):
                parts = vtp_konfig_zeile.split(":")
                vtp_mode = parts[1].strip()
            elif re.search(r"VTP version running", vtp_konfig_zeile):
                parts = vtp_konfig_zeile.split(":")
                vtp_version = parts[1].strip()
            elif re.search(r"VTP Domain Name", vtp_konfig_zeile):
                parts = vtp_konfig_zeile.split(":")
                vtp_domain = parts[1].strip()
            elif re.search(r"VTP Password", vtp_konfig_zeile):
                parts = vtp_konfig_zeile.split(":")
                vtp_password = parts[1].strip()
            elif re.search(r"Configuration Revision", vtp_konfig_zeile):
                parts = vtp_konfig_zeile.split(":")
                if int(parts[1].strip()) == 0:
                    break
        f.write(f"\nvtp mode {vtp_mode}\n")
        f.write(f"vtp version {vtp_version}\n")
        f.write(f"vtp domain {vtp_domain}\n")
        f.write(f"vtp password {vtp_password}\n")


if __name__ == "__main__":
    parse()
