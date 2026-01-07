# ITP_2526_TopoRecovery

Main git repository for the HTL3R ITP project TopoRecovery.

## Description

TopoRecovery is a Python project for reading out the configuration of virtualized Cisco-IOS Routers and Switches (in
GNS3).

## Requirements

- Python 3.12+
- numpy and clicker

## Required Libraries installation

Install the required libraries using pip:

```bash
pip install numpy click
```

## Usage (Windows)

### Clone the repository:

   ```powershell
   git clone https://github.com/r7d9Y/ITP_2526_TopoRecovery.git
   cd ITP_2526_TopoRecovery
   ```

### Run the main script:

   ```powershell
   python TopoRecover.py [options]
   ```

## Usage (Linux)

### Clone the repository:

   ```bash
   git clone https://github.com/r7d9Y/ITP_2526_TopoRecovery.git
   cd ITP_2526_TopoRecovery
   ```

### Run the main script:

   ```bash
   python3 TopoRecover.py [options]
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

#### Example usage (Windows):

```powershell
python TopoRecover.py --settings-path custom_settings.json
```

#### Example usage (Linux):

```bash
python3 TopoRecover.py --settings-path custom_settings.json
```

## License
This project is licensed under the  
#### GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007

