# Menagerie: A scriptable planner interface for Aquarium
Menagerie is a Python scripting interface for generating Aquarium Plans from high-level JSON descriptions.

## Contents

* [Requirements](#requirements)
* [Installation](#installation)
* [Use](#use)
* [Quick Start: Yeast Display](docs/quick_start_yeast_display.md)
* [Quick Start: NGS Prep](docs/quick_start_ngs_prep.md)
* [Customizing Plans](docs/customizing_plans.md)

## Requirements

Menagerie requires:

* [Docker](https://www.docker.com/get-started)
* An [Aquarium](https://www.aquarium.bio/) login

## Installation
### 1. Clone Menagerie
Get Menagerie using [git](https://git-scm.com/) with the command

```bash
git clone https://github.com/aquariumbio/menagerie.git
cd menagerie
```

### 2. Add credentials
In order to add credentials for your Aquarium instance(s), run
```bash
cp menagerie/util/secrets_template.json menagerie/util/secrets.json
```
and add your login and url information to the new file at `menagerie/util/secrets.json`. You can have more than two instances, and the names (e.g., `laptop` and `production`) can be changed to whatever you want them to be. You can add more names as long as they are all different.

```
{
  "laptop": {
    "login": "neptune",
    "password": "aquarium",
    "aquarium_url": "http://localhost/"
  },
  "production": {
    "login": "your_production_username",
    "password": "your_production_password",
    "aquarium_url": "production_production_url"
  }
}
```
Note: If you change or add to the `menagerie/util/secrets.json` file, you will need to re-run step #3 (Install).

### 3. Install
Run
```bash
sh menagerie-install.sh
```

## Use
### Plan NGS Prep From Parameters
Copy the file `config/yeast_display/template_ngs_prep_params/params.json` and rename it whatever you want.
Next, open the file in a text editor. You should see this:
```
{
  "input_samples": {
    "items": [1, 2, 3],
    "qpcr_1_forward_primer": "qPCR1 Forward Primer",
    "qpcr_1_reverse_primer": "qPCR1 Reverse Primer",
    "qpcr_2_forward_primer": "qPCR2 Forward Primer",
    "qpcr_2_reverse_primer": [
      "qPCR2 Reverse Primer 01",
      "qPCR2 Reverse Primer 02",
      "qPCR2 Reverse Primer 03"
    ]
  }
}
```
To customize the file for your plan, change
```
"items": [1, 2, 3]
```
so that it specifies the items you want to do NGS prep for. For example:
```
"items": [12345, 12346, 12347]
```
Next, change the names of the primers to the primers you would like to use. For example:
```
"qpcr_1_forward_primer": "Petcon Forward",
"qpcr_1_reverse_primer": "Petcon Reverse",
"qpcr_2_forward_primer": "Petcon NGS prep forward primer",
"qpcr_2_reverse_primer": [
      "P7-finish_TSBC01-r",
      "P7-finish_TSBC02-r",
      "P7-finish_TSBC03-r",
      "P7-finish_TSBC04-r",
      "P7-finish_TSBC05-r",
      "P7-finish_TSBC06-r",
      "P7-finish_TSBC07-r",
      "P7-finish_TSBC08-r",
      "P7-finish_TSBC09-r",
      "P7-finish_TSBC10-r",
      "P7-finish_TSBC11-r",
      "P7-finish_TSBC12-r",
      "P7-finish_TSBC13-r",
      "P7-finish_TSBC14-r"
]
```
Save the file, and run the app with the path to the folder that contains it, for example:
```bash
plan-ngs-prep /Users/devin/workspace/menagerie/config/yeast_display/template_ngs_prep_params/
```

## Development

For development, Menagerie can be run in a Visual Studio Code [dev container](https://code.visualstudio.com/remote-tutorials/containers/how-it-works). To take advantage of this environment, you will also need to install [Visual Studio Code](https://code.visualstudio.com/).

### Open in VS Code dev container
From a new VS Code window, open the Menagerie folder. You should see a dialog at the bottom right corner of the window that says **Folder contains a dev container configuration file. Reopen folder to develop in a container (learn more).** Select **Reopen in Container**. You can also click the green rectangle at the lower left corner and select **Remote-Containers: Reopen Folder in Container** from the menu that appears at the top of the window.

### Install Aquarium locally in a Docker container
Menagerie and Trident are able to make far-reaching modifications to the Aquarium database, and can launch computationally expensive queries on the server. It is highly recommended that you test any new code on a local Aquarium instance. You can install a local instance running in Docker by following [these instructions](https://github.com/klavinslab/aquarium-local).

Once you have Aquarium running locally, it is convenient to be able to backup and load versions of the database without having to restart the container. You can do that using the script `hot_swap_db.py` found [here](https://github.com/dvnstrcklnd/aq-hot-swap-db).
