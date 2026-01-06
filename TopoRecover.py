#       _____________________________________________
#      __/___  ____/\__/ ______ \____/ /\____/ /\___
#     ___\__/ /\_\_\/_/ /_____/ /\__/_/_/___/_/\/__
#    ______/ /\/_____/ ____  __/\/__\/_  __/\_\/__
#   ______/ /\/_____/ /\__\\ \_\/____\/ /\_\/____
#  ______/_/\/_____/_/\/___\\_\______/_/\/______
# _______\_\/______\_\/_____|_|______\_\/______

import json
import logging
import re
import sys
from pathlib import Path
import click
import shutil
import config_reader
import parser
from confer import Confer

logger = logging.getLogger(__name__)

FORMAT = '%(asctime)s %(message)s'
DATE_TIME_FORMAT = '%Y:%m:%d_%H:%M:%S'

DEFAULT_GENERAL_SETTINGS_FILE = Path("settings/general_settings.json")
FALLBACK_READER_SETTINGS = Path("settings/reader_settings.json")

RAW_OUTPUT_PATH = Path('raw_output')


def load_general_settings(path: Path = DEFAULT_GENERAL_SETTINGS_FILE) -> dict:
    """
    Loads the general settings from the specified JSON file. If the file cannot be loaded or is missing required keys,
    fallback settings are used.
    :param path: path to the general settings file
    :returns dict: loaded settings
    """
    try:
        logger.info(f"GENERAL_SETTINGS_LOADING from {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        reader_settings_path = Path(data["reader_settings_path"])
        if not isinstance(data["version"], str):
            raise TypeError("TYPE_ERROR: value of 'version' must be a string'")
        version = data["version"]
        logger.info(f"GENERAL_SETTINGS_LOADED version={version}, reader_settings_path={reader_settings_path}")
        return {
            "reader_settings_path": reader_settings_path,
            "version": version
        }
    except FileNotFoundError:
        logger.error(f"GENERAL_SETTINGS_FILE_NOT_FOUND at {path}")
        raise FileNotFoundError(f"GENERAL_SETTINGS_FILE_NOT_FOUND: currently at {path}")
    except json.JSONDecodeError:
        logger.error("GENERAL_SETTINGS_FILE_INVALID_JSON")
        raise Exception("GENERAL_SETTINGS_FILE contains invalid JSON.")
    except KeyError:
        logger.error("GENERAL_SETTINGS_FILE_MISSING_KEYS")
        raise KeyError("General settings file missing required keys: 'version', 'reader_settings_path'")
    except TypeError as e:
        logger.error(f"GENERAL_SETTINGS_TYPE_ERROR: {e}")
        raise TypeError(e)


def indexed_choice(options, prompt_text):
    """
    lists the options in a numerated list format, which can be selected by entering the index number of the list
    :param options: options to list
    :param prompt_text: prompt text information for the input of the user
    :return: returns the selected option
    """
    logger.debug(f"INDEXED_CHOICE_PRESENTED options={options} prompt='{prompt_text}'")
    for idx, val in enumerate(options):
        click.echo(f"{idx}: {val}")
    idx = click.prompt(prompt_text, type=click.IntRange(0, len(options) - 1))
    logger.info(f"INDEXED_CHOICE_SELECTED index={idx} value={options[idx]}")
    return options[idx]


def handle_command_section(settings: dict, settings_path: Path) -> bool:
    """
    handles the interactive setting edit of the command section
    :param settings: content of the settings file
    :param settings_path: setting path of the file to edit
    :return: returns False if no options are listed in one option, otherwise it continues until
    the user is finished and returns True
    """
    logger.info(f"COMMAND_SECTION_EDITING settings_path={settings_path}")
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
        logger.info(f"COMMAND_GROUP_ADDING device_type={device_type}")
        while True:
            cmd_type = click.prompt("Enter new command group name")
            if not cmd_type in commands.get(device_type, {}):
                break
            click.echo("Group already exists")

        new_cmds = click.prompt(f"Enter commands for {device_type} - {cmd_type} (comma separated)")
        # insert new command
        commands.setdefault(device_type, {})[cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
    elif action == 'edit':
        logger.info(f"COMMAND_GROUP_EDITING device_type={device_type}")
        group_names = list(commands.get(device_type, {}).keys())
        if not group_names:
            click.echo("No command groups to edit.")
            return False
        cmd_type = indexed_choice(group_names, f"Select command group index for {device_type}")
        new_cmds = click.prompt(f"Overwrite commands of {device_type} - {cmd_type} (comma separated)",
                                default=",".join(commands[device_type][cmd_type]))
        # insert new command
        commands[device_type][cmd_type] = [cmd.strip() for cmd in new_cmds.split(",") if cmd.strip()]
    elif action == 'remove':
        logger.info(f"COMMAND_GROUP_REMOVING device_type={device_type}")
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
    logger.info(f"COMMANDS_UPDATED settings_path={settings_path}")
    click.echo("Commands updated and saved.")
    return True


def is_valid_ip(ip: str) -> bool:
    """
    checks if the given ip is a valid IPv4 address
    :param ip: IPv4 address
    :return: True if valid IP, False otherwise
    """
    return bool(re.match(r"^(((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$|localhost)", ip))


def is_valid_port(port: str) -> bool:
    """
    checks if the given port is a valid port
    :param port: Port to check (0 <= port <= 65535)
    :return: True if valid port, False otherwise
    """
    try:
        port = int(port)
        return 0 <= port <= 65535
    except TypeError:
        return False


def is_valid_type(device_type: str) -> bool:
    """
    checks if the given type is valid
    :param device_type: given type has to be in ['router', 'switch']
    :return: True if valid, False otherwise
    """
    return device_type in ['router', 'switch']


def is_valid_ios(device_ios: str) -> bool:
    """
    checks if the given IOS string could be valid
    :param device_ios: ios string has to end with '_telnet'
    :return: True if valid, False otherwise
    """
    return device_ios.endswith('_telnet')


def is_valid_username(username: str) -> bool:
    """
    checks if the given username is valid, character wise
    :param username: username has to match with ^[A-Za-z0-9._@+$~!%:/\\-]{1,64}$ or it is 'None'
    :return: True if valid, False otherwise
    """
    # Regex allows alphanumeric characters and special characters . _ - @ + $ ~ ! % : / \ and a length of 0-64
    username_pattern = r'^[A-Za-z0-9._\-@+$~!%:/\\]{1,64}$'
    return (username and re.fullmatch(username_pattern, username) is not None) or username is None


def is_valid_pwd(pwd: str) -> bool:
    """
    checks if the given password is valid, character wise
    :param pwd: pwd has to match with ^[\x21-\x7E]+$ or it is 'None'
    :return: True if valid, False otherwise
    """
    pwd_pattern = r'^[\x21-\x7E]+$'
    return (pwd and re.fullmatch(pwd_pattern, pwd) is not None) or pwd is None


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
    logger.info(f"DEVICES_SECTION_EDITING settings_path={settings_path}")
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
        while True:
            ip = click.prompt("Enter device IP")
            if is_valid_ip(ip):
                break
            print("Wrong IP format, try again.")
        while True:
            port = click.prompt("Enter device port")
            if is_valid_port(port):
                if port in devices.get(ip, {}):
                    click.echo("Device already exists, use different port")
                    continue
                break
            print("Wrong port range (0 <= port <= 65535), try again.")
        logger.info(f"DEVICE_ADDING ip={ip} port={port}")
        while True:
            device_type = click.prompt("Enter device type (e.g., switch, router)")
            if is_valid_type(device_type):
                break
            print("Wrong device type. Has to be in [switch, router]")
        while True:
            device_ios = click.prompt("Enter device_ios (e.g., cisco_ios_telnet)")
            if is_valid_ios(device_ios):
                break
            print("Wrong device_ios. Must end with '_telnet'. (e.g.: cisco_ios_telnet)")
        while True:
            username = click.prompt("Enter username (Enter 'None' if not wanted)")
            if is_valid_username(username):
                break
            print("Not valid username. Must match: ^[A-Za-z0-9._@+$~!%:/\\-]{1,64}$ or 'None'")
        while True:
            password = click.prompt("Enter password (Enter 'None' if not wanted)", hide_input=True)
            if is_valid_pwd(password):
                break
            print("No valid password entered, try again. Must match '^[\x21-\x7E]+$' or 'None'")
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
        logger.info(f"DEVICE_EDITING ip={ip} port={port}")
        # editable properties
        editable_keys = ['device_type', 'device_ios', 'username', 'password']
        # asks the user for input until valid input
        while True:
            key = indexed_choice(editable_keys, "Select property to edit (or Ctrl+C to finish)")
            while True:
                if key in ['username', 'password']:
                    value = click.prompt(f"Enter new value for {key} (Enter 'None' if not wanted)", default="",
                                         show_default=False, hide_input=(key == 'password'))
                else:
                    value = click.prompt(f"Enter new value for {key}", default=props.get(key, ""))
                if key == 'username' and not is_valid_username(value):
                    print("Not valid username. Must match: ^[A-Za-z0-9._@+$~!%:/\\-]{1,64}$ or 'None'")
                    continue
                if key == 'password' and not is_valid_pwd(value):
                    print("No valid password entered, try again. Must match '^[\x21-\x7E]+$' or 'None'")
                    continue
                if key == 'device_type' and not is_valid_type(value):
                    print("Wrong device type. Has to be in [switch, router]")
                    continue
                if key == 'device_ios' and not is_valid_ios(value):
                    print("Wrong device_ios. Must end with '_telnet'. (e.g.: cisco_ios_telnet)")
                    continue
                break
            devices[ip][port][key] = value
            if not click.confirm("Edit another property for this device?", default=False):
                break
    elif action == 'remove':
        if not device_list:
            click.echo("No devices to remove.")
            return False
        idx = click.prompt("Select device index to remove", type=click.IntRange(0, len(device_list) - 1))
        ip, port, _ = device_list[idx]
        logger.info(f"DEVICE_REMOVING ip={ip} port={port}")
        del devices[ip][port]
        if not devices[ip]:
            del devices[ip]

    # writes new section to the given path
    settings['devices'] = devices
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    logger.info(f"DEVICES_UPDATED settings_path={settings_path}")
    click.echo("Devices updated and saved.")
    return True


def edit_settings_interactive(settings_path) -> None:
    """
    handles the interaction to interactively edit the settings file of given path. This function is called if the
    ``--edit_settings`` flag is set.
    :param settings_path: path to the settings file to edit
    :return: ``None``
    """
    logger.info(f"EDIT_SETTINGS_INTERACTIVE_START settings_path={settings_path}")
    if not settings_path.exists():
        click.echo(f"Settings file {settings_path} not found.")
        return

    with open(settings_path, 'r') as f:
        settings = json.load(f)

    section = click.prompt("Edit 'devices' or 'commands'?", type=click.Choice(['devices', 'commands', 'd', 'c']),
                           show_choices=True)

    # if option command is taken
    if section == 'commands' or section == 'c':
        logger.info("EDIT_SETTINGS_INTERACTIVE_COMMANDS_SELECTED")
        if not handle_command_section(settings, settings_path):
            return
    elif section == 'devices' or section == 'd':
        logger.info("EDIT_SETTINGS_INTERACTIVE_DEVICES_SELECTED")
        if not handle_devices_section(settings, settings_path):
            return


def generate_reader_settings_template(filename,
                                      template_path: Path = Path('settings/reader_settings_template.json')) -> bool:
    """
    Generates a settings template file at `filename`.
    If `template_path` exists and contains valid JSON it will be used as the template, otherwise a built-in fallback template is written.

    :param filename: destination filename for the generated settings file
    :type filename: str or pathlib.Path
    :param template_path: optional path to a JSON template to use instead of the builtin one
    :type template_path: pathlib.Path
    :return: True if the file was created successfully, False otherwise
    :rtype: bool
    """
    logger.info(f"READER_SETTINGS_TEMPLATE_GENERATING filename={filename} template_path={template_path}")
    # builtin fallback template
    fallback_template = {
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

    # try to load template from file, otherwise use fallback
    try:
        template = fallback_template
        tpl_path = Path(template_path)
        if tpl_path.exists():
            with open(tpl_path, 'r', encoding='utf-8') as tf:
                template = json.load(tf)
        logger.info(f"READER_SETTINGS_TEMPLATE_LOADED tpl_path={tpl_path}")
    except json.JSONDecodeError:
        click.echo(
            f"Template file `{template_path}` contains invalid JSON; using builtin fallback for reader settings template creation.")
        template = fallback_template
    except Exception as e:
        click.echo(f"Error reading template `{template_path}`: {e}; using builtin fallback.")
        template = fallback_template

    # write the template to the destination
    try:
        dest_path = Path(filename)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        logger.info(f"READER_SETTINGS_TEMPLATE_WRITTEN filename={filename}")
        click.echo(f"Template settings file written to `{filename}`")
        return True
    except Exception as e:
        logger.error(f"READER_SETTINGS_TEMPLATE_WRITE_ERROR filename={filename} error={e}")
        click.echo(f"Could not create template settings file at `{filename}`: {e}")
        return False


def upload_configuration_to_devices(conf_file: str, device_type: str, ip: str, port: int, username: str = None,
                                    password: str = None) -> bool:
    logger.info(f"UPLOAD_CONFIGURATION_START ip={ip} port={port} device_type={device_type} conf_file={conf_file}")
    try:
        confer = Confer(conf_file, device_type, ip, port, username, password)
        confer.send_cmds()
        logger.info(f"UPLOAD_CONFIGURATION_SUCCESS ip={ip} port={port}")
        return True
    except Exception as e:
        logger.error(f"UPLOAD_CONFIGURATION_ERROR ip={ip} port={port} error={e}")
        return False


@click.command()
@click.option('--edit-settings', is_flag=True, help='Edit the settings file interactively.')
@click.option('--settings-path', metavar='FILENAME', help='Change path to use different settings file.')
@click.option('--generate-template', metavar='FILENAME', help='Generate a template settings file.')
@click.option('--upload-config', is_flag=True, help='Upload a configuration to device.')
@click.option('--version', is_flag=True, help='Show program version and exit.')
@click.option('--clear-output', is_flag=True,
              help='Delete all files in output/ & raw_output/ folders.')
def main(edit_settings, settings_path, generate_template, upload_config, version, clear_output):
    """
    This program runs the TopoRecovery tool, which retrieves configurations from network devices,
    parses them and stores the read config. Logs are stored in the logs/log.txt file.
    The program can be configured using a settings file, which can be edited interactively.
    Alternatively, a template settings file can be generated for manual editing.

    The Options will only do their specific task and then exit the program.

    """
    try:
        # ensure logs directory and `logs/log.txt` exist and are usable
        logs_dir = Path("logs")
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / "log.txt"
            if not log_file.exists():
                log_file.touch(mode=0o644, exist_ok=True)
            # verify file is readable/writable
            with open(log_file, "a+", encoding="utf-8") as f:
                f.seek(0)
                f.read(0)
        except Exception as e:
            click.echo(f"Could not create or access `logs/log.txt`: {e}")
            sys.exit(1)

        # initializes the logger, the date format and format are defined at the top
        logging.basicConfig(filename='logs/log.txt',
                            datefmt=DATE_TIME_FORMAT,
                            format=FORMAT,
                            level=logging.INFO
                            )
        logger.info("LOGGER_INITIALIZED")
        # load general settings
        general = load_general_settings()
        program_version = general["version"]
        script_setting_path = general["reader_settings_path"]
        logger.info(f"GENERAL_SETTINGS_USED version={program_version} reader_settings_path={script_setting_path}")
        if not Path(script_setting_path).exists():
            logger.error("SCRIPT_SETTINGS_FILE_NOT_FOUND")
            raise FileNotFoundError("SCRIPT_SETTINGS_FILE_NOT_FOUND")
        # handles the version option
        if version:
            logger.info(f"VERSION_REQUESTED version={program_version}")
            click.echo(f"TopoRecovery version {program_version}")
            sys.exit(0)
        # modifies the default function of the script to use different settings file for reading the configurations
        if settings_path:
            script_setting_path = Path(settings_path)
            logger.info(f"SETTINGS_PATH_OVERRIDE path={script_setting_path}")
            if not script_setting_path.exists():
                logger.warning("SETTINGS_FILE_NOT_FOUND")
                sys.exit("Settings file not found")
        # handles the generate template option
        if generate_template:
            logger.info(f"GENERATE_TEMPLATE_REQUESTED filename={generate_template}")
            successful = generate_reader_settings_template(generate_template)
            if successful:
                click.echo(f"TEMPLATE_SETTINGS_FILE_GENERATED")
            else:
                click.echo(f"COULD_NOT_GENERATE_TEMPLATE_SETTINGS_FILE")
            sys.exit(0)
        # handles the edit settings option
        if edit_settings:
            logger.info("EDIT_SETTINGS_REQUESTED")
            edit_settings_interactive(script_setting_path)
            sys.exit(0)
        # handles the upload configuration option
        if upload_config:
            logger.info("UPLOAD_CONFIGURATION_REQUESTED")
            # Prompt for all required parameters interactively
            conf_file = click.prompt("Enter configuration file to upload")
            device_ios = click.prompt("Enter device IOS (e.g.: cisco_ios_telnet)")
            ip = click.prompt("Enter device IP address")
            port = click.prompt("Enter device port", type=int)
            username = click.prompt("Enter device username")
            password = click.prompt("Enter device password", hide_input=True)
            logger.info(f"UPLOAD_CONFIGURATION_INPUTS conf_file={conf_file} device_ios={device_ios} ip={ip} port={port} username={username}")
            success = upload_configuration_to_devices(conf_file, device_ios, ip, port, username, password)
            if success:
                click.echo("Configuration uploaded successfully.")
            else:
                click.echo("Failed to upload configuration.")
            sys.exit(0)
        # handle the clear-output option
        if clear_output:
            logger.info("CLEAR_OUTPUT_REQUESTED")
            # remove all files in output/ and raw_output/ directories
            for folder in [Path('output'), Path('raw_output')]:
                if folder.exists() and folder.is_dir():
                    for item in folder.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
            click.echo("Cleared output/ and raw_output/ folders.")
            logger.info("OUTPUT_FOLDERS_CLEARED")
            exit(0)
        # if the program reaches this point, it executes the config_reader and parser
        try:
            logger.info(f"CONFIG_READER_EXECUTE path={RAW_OUTPUT_PATH} settings={script_setting_path}")
            config_reader.ConfigReader(RAW_OUTPUT_PATH, script_setting_path).execute()
            logger.info("CONFIG_READER_EXECUTED")
        except Exception as e:
            logger.error(f"CONFIG_READER_ERROR error={e}")
            click.echo(f"Error running config reader: {e}")
            sys.exit(1)
        for raw_output_file in RAW_OUTPUT_PATH.glob("*_raw_config.txt"):
            file_name = raw_output_file.name
            p = re.compile(r"((\d{1,3}\.){3}\d{1,3})_(\d{4,5})-\d{4}(_\d{2}){2}-(\d{2}_){3}raw_config\\.txt")
            matches = p.match(file_name)
            if matches is None:
                logger.debug(f"RAW_CONFIG_FILE_SKIPPED file_name={file_name}")
                continue
            try:
                logger.info(f"RAW_CONFIG_FILE_PARSING file={raw_output_file} ip={matches.group(1)} port={matches.group(3)}")
                parser.parse(raw_output_file, matches.group(1), matches.group(3))
                logger.info(f"RAW_CONFIG_FILE_PARSED file={raw_output_file} ip={matches.group(1)} port={matches.group(3)}")
            except Exception as e:
                logger.error(f"RAW_CONFIG_FILE_PARSE_ERROR file={raw_output_file} ip={matches.group(1)} port={matches.group(3)} error={e}")
                click.echo(f"Error parsing {raw_output_file}: {e}")
                continue
            raw_output_file.unlink()
            logger.info(f"RAW_CONFIG_FILE_DELETED file={raw_output_file} ip={matches.group(1)} port={matches.group(3)}")
    except KeyboardInterrupt:
        logger.warning("PROGRAM_INTERRUPTED_BY_USER")
        click.echo("Program interrupted by user, exiting...")
        sys.exit(130)
    except Exception as e:
        logger.error(f"UNHANDLED_EXCEPTION error={e}", exc_info=True)
        click.echo(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
