#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import re

with open("./raw_output_testdatei.txt", "r", encoding="utf-8") as f:
    zeilen = f.readlines()  # Liste mit alle Zeilen

with open("output.txt", "w") as f:

    start_index = 0
    for index, line in enumerate(zeilen):  # enumerate gibt Index und Zeile
        if re.search(r"\*\* start vlan \*\*", line):
            start_index = index
            break

    # VLAN-Nummern + Name ermitteln
    for vlan_konfig_zeile in zeilen[start_index:]:
        if not vlan_konfig_zeile[0].isdigit() or vlan_konfig_zeile[0].isdigit() and int(vlan_konfig_zeile[:4].strip()) < 1001:
            if vlan_konfig_zeile[0].isdigit() and int(vlan_konfig_zeile[:4].strip()) != 1:
                vlan_nummer: str = ""
                vlan_name: str = ""
                parts = vlan_konfig_zeile.split() # Zeile an Leerzeichen teilen
                vlan_nummer = parts[0]
                vlan_name = parts[1]
                f.write(f"vlan {vlan_nummer} \nname {vlan_name}\n")
        else:
            break