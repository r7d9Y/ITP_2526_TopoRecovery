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

DEFAULT_SETTINGS_FILE = 'settings.json'


def indexed_choice(options, prompt_text):
    for idx, val in enumerate(options):
        click.echo(f"{idx}: {val}")
    idx = click.prompt(prompt_text, type=click.IntRange(0, len(options) - 1))
    return options[idx]


def edit_settings_interactive(settings_path):
    if not os.path.exists(settings_path):
        click.echo(f"Settings file {settings_path} not found.")
        return

    with open(settings_path, 'r') as f:
        settings = json.load(f)

    section = click.prompt("Edit 'devices' or 'commands'?", type=click.Choice(['devices', 'commands']),
                           show_choices=True)

    if section == 'commands':
        commands = settings.get('commands', {})
        for device_type in ['router', 'switch']:
            click.echo(f"\nCurrent commands for {device_type}:")
            for cmd_type, cmd_list in commands.get(device_type, {}).items():
                click.echo(f"  {cmd_type}: {cmd_list}")

        device_type = indexed_choice(['router', 'switch'], "Select device type index")
        action = indexed_choice(['add', 'edit', 'remove'], "Select action index")

        if action == 'add':
            cmd_type = click.prompt("Enter new command group name")
            new_cmds = click.prompt(f"Enter commands for {device_type} - {cmd_type} (comma separated)")
            commands.setdefault(device_type, {})[cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
        elif action == 'edit':
            group_names = list(commands.get(device_type, {}).keys())
            if not group_names:
                click.echo("No command groups to edit.")
                return
            cmd_type = indexed_choice(group_names, f"Select command group index for {device_type}")
            new_cmds = click.prompt(f"Enter new commands for {device_type} - {cmd_type} (comma separated)",
                                    default=",".join(commands[device_type][cmd_type]))
            commands[device_type][cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
        elif action == 'remove':
            group_names = list(commands.get(device_type, {}).keys())
            if not group_names:
                click.echo("No command groups to remove.")
                return
            cmd_type = indexed_choice(group_names, f"Select command group index to remove for {device_type}")
            del commands[device_type][cmd_type]

        settings['commands'] = commands
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        click.echo("Commands updated and saved.")


    elif section == 'devices':
        devices = settings.get('devices', {})
        click.echo("\nCurrent devices:")
        device_list = []
        for ip, ports in devices.items():
            for port, props in ports.items():
                device_list.append((ip, port, props))
        for idx, (ip, port, props) in enumerate(device_list):
            click.echo(f"{ip}:{port} [{idx}] -> {props}")

        action = indexed_choice(['add', 'edit', 'remove'], "Select action index")

        if action == 'add':
            ip = click.prompt("Enter device IP")
            port = click.prompt("Enter device port")
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
                return
            idx = click.prompt("Select device index to edit", type=click.IntRange(0, len(device_list) - 1))
            ip, port, props = device_list[idx]
            editable_keys = ['device_type', 'device_ios', 'username', 'password']
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
                return
            idx = click.prompt("Select device index to remove", type=click.IntRange(0, len(device_list) - 1))
            ip, port, _ = device_list[idx]
            del devices[ip][port]
            if not devices[ip]:
                del devices[ip]

        settings['devices'] = devices
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        click.echo("Devices updated and saved.")


def generate_settings_template(filename):
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
@click.option('--generate-template', metavar='FILENAME', help='Generate a template settings file')

def main(edit_settings, generate_template):
    if generate_template:
        generate_settings_template(generate_template)
        sys.exit(0)
    if edit_settings:
        edit_settings_interactive(DEFAULT_SETTINGS_FILE)
        sys.exit(0)

    logging.basicConfig(filename='log.txt',
                        datefmt=DATE_TIME_FORMAT,
                        format=FORMAT,
                        level=logging.INFO
                        )
    # logger.info('Started')
    config_reader.ConfigReader().execute()
    parser.parse("raw_output.txt", "1.2.3.4", 80)
    # logger.info('Finished')


if __name__ == '__main__':
    main()
