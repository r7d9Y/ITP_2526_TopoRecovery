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
    with open("./matchlist", "r", encoding="utf-8") as f:
        std = f.readlines()
    with open("output.txt", "w") as f:
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
        run="".join(s for s in run if s.strip() and not s.lstrip().startswith("!"))# idk was da bei den regexes abgeht, die machen iwas
#        run = re.sub(r"(([\n\r]) *!.*)+", "\n", run, re.M)
        run = re.sub(r"(((line)|(interface)|(router)).*)", r"\n\1", run, re.M)
        run = re.sub(r"\n{2,}", "\n\n", run, re.M)
        for i in range(len(std)):
            line = std[i]
            if not line.startswith("g"):
                fc = line[0]
                line = line[1:]
                if fc == "l":
                    line = re.escape(line)
                re.sub(line, "", run)

        del std
        f.write(run)
        # ------
        # VLAN-Konfig erstellen und in das Output-File schreiben
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
                    if int(parts[1].strip()) == 1:
                        write_konfig = True
        if write_konfig:  # wenn die Variable auf True gesetzt wurde, werden alle Elemente aus der Liste in das Output-File geschrieben
            f.writelines(vtp_commands_to_write)


if __name__ == "__main__":
    parse()
