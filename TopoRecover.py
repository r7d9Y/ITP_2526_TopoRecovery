import re
from pathlib import Path
from re import Pattern

import config_reader
import json
import os
import sys

import parser
import logging
import click

logger = logging.getLogger(__name__)

FORMAT = '%(asctime)s_%(ip)s:%(port)s--%(message)s'
DATE_TIME_FORMAT = '%Y:%m:%d_%H:%M:%S'

DEFAULT_SETTINGS_FILE = Path('./settings.json')


def indexed_choice(options, prompt_text):
    """
    lists the options in a numerated list format, which can be selected by entering the index number of the list
    :param options: options to list
    :param prompt_text: prompt text information for the input of the user
    :return: returns the selected option
    """
    for idx, val in enumerate(options):
        click.echo(f"{idx}: {val}")
    idx = click.prompt(prompt_text, type=click.IntRange(0, len(options) - 1))
    return options[idx]


def handle_command_section(settings: dict, settings_path: Path) -> bool:
    """
    handles the interactive setting edit of the command section
    :param settings: content of the settings file
    :param settings_path: setting path of the file to edit
    :return: returns False if no options are listed in one option, otherwise it continues until
    the user is finished and returns True
    """
    # lists the show commands of router and switch section
    commands = settings.get('commands', {})
    for device_type in ['router', 'switch']:
        click.echo(f"\nCurrent commands for {device_type}:")
        for cmd_type, cmd_list in commands.get(device_type, {}).items():
            click.echo(f"  {cmd_type}: {cmd_list}")

    # next click options
    device_type = indexed_choice(['router', 'switch'], "Select device type index")
    action = indexed_choice(['add', 'edit', 'remove'], "Select action index")

    # handle the action option
    if action == 'add':
        cmd_type = click.prompt("Enter new command group name")
        if cmd_type in commands.get(device_type, {}):
            click.echo("Group already exists")
            return False
        new_cmds = click.prompt(f"Enter commands for {device_type} - {cmd_type} (comma separated)")
        # insert new command
        commands.setdefault(device_type, {})[cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
    elif action == 'edit':
        group_names = list(commands.get(device_type, {}).keys())
        if not group_names:
            click.echo("No command groups to edit.")
            return False
        cmd_type = indexed_choice(group_names, f"Select command group index for {device_type}")
        new_cmds = click.prompt(f"Enter new commands for {device_type} - {cmd_type} (comma separated)",
                                default=",".join(commands[device_type][cmd_type]))
        # insert new command
        commands[device_type][cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
    elif action == 'remove':
        group_names = list(commands.get(device_type, {}).keys())
        if not group_names:
            click.echo("No command groups to remove.")
            return False
        cmd_type = indexed_choice(group_names, f"Select command group index to remove for {device_type}")
        del commands[device_type][cmd_type]

    # writes the commands section in the file destination
    settings['commands'] = commands
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    click.echo("Commands updated and saved.")
    return True


def handle_devices_section(settings: dict, settings_path: Path) -> bool:
    """
    Interactive management of the ``devices`` section in the settings.

    The function lists all currently configured devices and allows the user to
    add, edit, or remove devices via a selection menu. After changes, the
    updated ``devices`` block is written back into the provided ``settings``
    structure and saved as a JSON file at ``settings_path``.

    Actions
    -------
    - add: Adds a new device with ``ip``, ``port``, ``device_type``, ``device_ios``, ``username``, and ``password``. If the chosen port already exists for the IP, the operation is aborted.

    - edit: Edits the properties (``device_type``, ``device_ios``, ``username``, ``password``) of a selected device. ``username`` and ``password`` may be set to empty values.

    - remove: Removes a selected device. If no ports remain for an IP after removal, the entire IP entry is deleted.

    :param settings: Content of the settings file.
    :type settings: dict
    :param settings_path: Path to the settings file to edit.
    :type settings_path: pathlib.Path
    :return: ``False`` if a needed selection had no available options (for example, nothing to edit or remove); otherwise ``True`` after successful completion.
    :rtype: bool
    """
    devices = settings.get('devices', {})
    # lists the current devices with the configurations
    click.echo("\nCurrent devices:")
    device_list = []
    for ip, ports in devices.items():
        for port, props in ports.items():
            device_list.append((ip, port, props))
    for idx, (ip, port, props) in enumerate(device_list):
        click.echo(f"{ip}:{port} [{idx}] -> {props}")

    action = indexed_choice(['add', 'edit', 'remove'], "Select action index")

    if action == 'add':
        # prompts each property for userinput
        ip = click.prompt("Enter device IP")
        port = click.prompt("Enter device port")
        if port in devices.get(ip, {}):
            click.echo("Device already exists, use different port")
            return False
        device_type = click.prompt("Enter device type (e.g., switch, router)")
        device_ios = click.prompt("Enter device_ios (e.g., cisco_ios_telnet)")
        username = click.prompt("Enter username")
        password = click.prompt("Enter password", hide_input=True)
        devices.setdefault(ip, {})[port] = {
            "device_type": device_type,
            "device_ios": device_ios,
            "username": username,
            "password": password
        }
    elif action == 'edit':
        if not device_list:
            click.echo("No devices to edit.")
            return False
        idx = click.prompt("Select device index to edit", type=click.IntRange(0, len(device_list) - 1))
        ip, port, props = device_list[idx]
        # editable properties
        editable_keys = ['device_type', 'device_ios', 'username', 'password']
        # asks the user for input until valid input
        while True:
            key = indexed_choice(editable_keys, "Select property to edit (or Ctrl+C to finish)")
            if key in ['username', 'password']:
                value = click.prompt(f"Enter new value for {key} (leave empty for blank)", default="",
                                     show_default=False, hide_input=(key == 'password'))
            else:
                value = click.prompt(f"Enter new value for {key}", default=props.get(key, ""))
            devices[ip][port][key] = value
            if not click.confirm("Edit another property for this device?", default=False):
                break
    elif action == 'remove':
        if not device_list:
            click.echo("No devices to remove.")
            return False
        idx = click.prompt("Select device index to remove", type=click.IntRange(0, len(device_list) - 1))
        ip, port, _ = device_list[idx]
        del devices[ip][port]
        if not devices[ip]:
            del devices[ip]

    # writes new section to the given path
    settings['devices'] = devices
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    click.echo("Devices updated and saved.")
    return True


def edit_settings_interactive(settings_path=DEFAULT_SETTINGS_FILE):
    """
    handles the interaction to interactively edit the settings file of given path. This function is called if the
    --edit_settings flag is set.
    :param settings_path: path to the settings file to edit
    :return:
    """
    if not settings_path.exists():
        click.echo(f"Settings file {settings_path} not found.")
        return

    with open(settings_path, 'r') as f:
        settings = json.load(f)

    section = click.prompt("Edit 'devices' or 'commands'?", type=click.Choice(['devices', 'commands']),
                           show_choices=True)

    # if option command is taken
    if section == 'commands':
        if not handle_command_section(settings, settings_path):
            return
    elif section == 'devices':
        if not handle_devices_section(settings, settings_path):
            return


def generate_settings_template(filename):
    """
    generates a template for a custom settings file in given path
    :param filename:
    :return:
    """
    template = {
        "devices": {
            "<ip>": {
                "<port>": {
                    "device_type": "",
                    "device_ios": "",
                    "username": "",
                    "password": ""
                }
            }
        },
        "commands": {
            "router": {
                "group1": ["", ""]
            },
            "switch": {
                "group1": ["", ""]
            }
        }
    }
    with open(filename, 'w') as f:
        json.dump(template, f, indent=2)
    click.echo(f"Template settings file written to {filename}")


@click.command()
@click.option('--edit-settings', is_flag=True, help='Edit the settings file interactively')
@click.option('--settings-path', metavar='FILENAME', help='Change path to use different settings file')
@click.option('--generate-template', metavar='FILENAME', help='Generate a template settings file')
def main(edit_settings, settings_path, generate_template):
    """
    initialises the logger and executes the config_reader and parser
    with the optional options
    :param edit_settings: set this parameter, to edit the settings file ./settings.json
    :param generate_template: set this parameter, to generate a template for a custom setting file
    :param settings_path: set this parameter to change the path for the settings file to use
    :return:
    """
    script_setting_path = DEFAULT_SETTINGS_FILE
    if settings_path:
        script_setting_path = Path(settings_path)
        if not script_setting_path.exists():
            sys.exit("Settings file not found")
    if generate_template:
        generate_settings_template(generate_template)
        sys.exit(0)
    if edit_settings:
        edit_settings_interactive(script_setting_path)
        sys.exit(0)


    logging.basicConfig(filename='log.txt',
                        datefmt=DATE_TIME_FORMAT,
                        format=FORMAT,
                        level=logging.INFO
                        )

    config_reader.ConfigReader().execute()

    RAW_OUTPUT_PATH = Path('raw_output')
    for raw_output_file in RAW_OUTPUT_PATH.glob("*_raw_config.txt"):
        #checks if the name is in correct format
        file_name = raw_output_file.name
        p = re.compile(r"((\d{1,3}\.){3}\d{1,3})_(\d{4,5})-\d{4}(_\d{2}){2}-(\d{2}_){3}raw_config\.txt")
        matches = p.match(file_name)
        if len(matches.groups()) == 0:
            continue
        #parses raw_config file and deletes it afterward
        parser.parse(raw_output_file, matches.group(1), matches.group(3))
        raw_output_file.unlink()


if __name__ == '__main__':
    main()
