# ITP_2526_TopoRecovery

Git repository for the HTL3R ITP project TopoRecovery.

## Description

TopoRecovery is a Python project for reading out the configuration of virtualized Cisco-IOS Routers and Switches (in
GNS3).

## Requirements

- Python 3.12+
- numpy and clicker

## Setup Instructions

Follow these steps to set up your environment after cloning the repository.

### Windows

1. Clone the repository and navigate into it:
   ```powershell
   git clone https://github.com/r7d9Y/ITP_2526_TopoRecovery.git
   cd ITP_2526_TopoRecovery
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install the required libraries:
   ```powershell
   pip install netmiko click
   ```

### Linux

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/r7d9Y/ITP_2526_TopoRecovery.git
   cd ITP_2526_TopoRecovery
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required libraries:
   ```bash
   pip install netmiko click
   ```

## Usage

Test if the installation was successful:

```bash
   python TopoRecover.py --version
   ```

If successful, it should output the current version of the program.

#### Run the main script:

```bash
   python TopoRecover.py [option]
   ```

## Script Options

The main script (`TopoRecover.py`) supports the following options:

- `--edit-settings`  
  Edit the settings file interactively.
- `--settings-path <FILENAME>`  
  Change path to use a different settings file.
- `--generate-template <FILENAME>`  
  Generate a template settings file.
- `--upload-config`  
  Upload a configuration to a device.
- `--version`  
  Show program version and exit.
- `--clear-output`  
  Delete all files in `output/` & `raw_output/` folders.
- `--help`  
  Show help message and exit.

#### Example usage:

```bash
python TopoRecover.py --settings-path custom_settings.json
```

## License

This project is licensed under the

#### GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007
