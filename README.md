# Menagerie: A scriptable planner interface for Aquarium
Menagerie is a Python scripting interface for generating Aquarium Plans from high-level JSON descriptions.

## Requirements

Menagerie requires:

* [Trident](https://github.com/klavinslab/trident)
* An Aquarium login

Menagerie is designed to be run in a Visual Studio Code [dev container](https://code.visualstudio.com/remote-tutorials/containers/how-it-works). To take advantage of this environment, you will also need to:

* Install [Docker](https://www.docker.com/get-started)
* Install [Visual Studio Code](https://code.visualstudio.com/)

Running Menagerie in this environment eliminates the need to install Trident or manage your Python version. 

## Setup
### 1. Clone Menagerie
Get Menagerie using [git](https://git-scm.com/) with the command

```bash
git clone https://github.com/klavinslab/menagerie.git
```

### 2. Open in VS Code dev container
From a new VS Code window, open the Menagerie folder. You should see a dialog at the bottom right corner of the window that says **Folder contains a dev container configuration file. Reopen folder to develop in a container (learn more).** Select **Reopen in Container**. You can also click the green rectangle at the lower left corner and select **Remote-Containers: Reopen Folder in Container** from the menu that appears at the top of the window. 

### 3. Add credentials
In order to add credentials for your Aquarium instance(s), `cp util/secrets_template.json util/secrets.json`, and add your login and url information to the new file. You can have more than two instances, and the keys (e.g., `laptop` and `production`) can be changed to whatever you want them to be.

```json
{
  "laptop": {
    "login": "neptune",
    "password": "aquarium",
    "aquarium_url": "http://localhost:3000/"
  },
  "production": {
    "login": "your_production_username",
    "password": "your_production_password",
    "aquarium_url": "production_production_url"
  }
}
```

### 4. Install Aquarium locally in a Docker container
Menagerie and Trident are able to make far-reaching modifications to the Aquarium database, and can launch computationally expensive queries on the server. It is highly recommended that you test any new code on a local Aquarium instance. You can install a local instance running in Docker by following [these instructions](https://www.aquarium.bio/?category=Getting%20Started&content=Docker%20Installation).

## Quick Start

### Plan a protein stability (yeast display) experiment
This section describes the steps for planning a three-round yeast display selection experiment following Gabe Rocklin's [massively parallel measurement of protein stability](https://www.ncbi.nlm.nih.gov/pubmed/28706065). It is best to run this initially on a local Dockerized instance of Aquarium. If you haven't done so already, you can find steps for installing a Dockerized Aquarium instance [here](https://www.docker.com/get-started).

Once you have Aquarium running locally, it is convenient to be able to backup and load versions of the database without having to restart the container. You can do that using the script `hot_swap_db.py` found [here](https://github.com/dvnstrcklnd/aq-hot-swap-db).

You will need to download and install three workflow libraries. You can find instructions for installing workflows [here](https://www.aquarium.bio/?category=Community&content=Importing). It is a good idea to backup the database before importing. The libraries are:

* [Standard Libraries](https://github.com/klavinslab/standard-libraries)
* [Flow Cytometry](https://github.com/klavinslab/flow-cytometry)
* [Yeast Display](https://github.com/dvnstrcklnd/aq-yeast-display)

It is also a good idea to back up the database (using a distinct file name) after importing these. 

Next, you will need to populate the database with some `Samples`. To do this, open the VS Code terminal using `^~` and run 

```bash
python util/load_test_samples.py 
```

From the browser, you should see that the following `Samples` are loaded:
```
►	6: Anti-c-myc-FITC		
►	5: Chymotrypsin		
►	4: Trypsin		
►	3: AMA1-best		
►	2: EBY100 + PETCONv3_baker		
►	1: DNA LIBRARY SAMPLE NAME
```

You can again back up the database (using a third distinct file name) after creating these.

Next, from the VS Code terminal, run: 
```bash
python plan_protein_stability.py -t
```

Menagerie uses several classes to manage the conversion of a JSON-formatted plan into an Aquarium `Plan` object.

## Customizing Plans

### JSON Files
There are 3 files that Menagerie takes as input.

`aquarium_defaults.json` is a file that contains configurations for Aquarium `Operations` that don't change very much, or have easily enumerable options. It contains a list of objects under the key `operation_defaults`:
```json
{
  "operation_defaults": [
    {
      "name": "Challenge and Label",
      "input": {
        "Antibody": {
          "object_type": [
            {
              "name": "Antibody Stock"
            }
          ],
          "sample": [
            {
              "name": "Anti-c-myc-FITC"
            }
          ]
        },
        "Protease": {
          "object_type": [
            {
              "name": "Protease Stock"
            }
          ]
        },
        "Protease Concentration": {
          "value": [
            {
              "value": 250
            }
          ]
        },
        "Yeast Culture": {
          "object_type": [
            {
              "name": "Yeast Library Liquid Culture",
              "option_key": "library"
            },
            {
              "name": "Yeast 50ml culture",
              "option_key": "control"
            }
          ]
        }
      },
      "output": {
        "Labeled Yeast Library": {
          "object_type": [
            {
              "name": "Labeled Yeast Library Suspension",
              "option_key": "library"
            },
            {
              "name": "Labeled Yeast Strain Suspension",
              "option_key": "control"
            }
          ]
        }
      }
    }
  ]
}
```

`params.json` is similar to `aquarium_defaults.json` but it specifies defaults that are specific to your experiment but applied to all samples in the experiment. It is not currently supported.

`plan.json` specifies the Aquarium `Samples` and operational flow that uniquely comprise your experiment. It usually contains several parts called `steps`. The first step is sometimes the `provision` step:
```json
{
  "id": 1,
  "name": "Provision Samples",
  "type": "provision",
  "operator": {
    "samples": [
      {
        "name": "DNA LIBRARY SAMPLE NAME",
        "sample_type": "DNA Library",
        "sample_key": "library"
      },
      {
        "name": "EBY100 + PETCONv3_baker",
        "sample_type": "Yeast Strain",
        "sample_key": "binding_negative"
      },
      {
        "name": "AMA1-best",
        "sample_type": "Yeast Strain",
        "sample_key": "fitc_binding_positive"
      },
      {
        "name": "Trypsin",
        "sample_type": "Protease",
        "sample_key": "trypsin"
      },
      {
        "name": "Chymotrypsin",
        "sample_type": "Protease",
        "sample_key": "chymotrypsin"
      },
      {
        "name": "Anti-c-myc-FITC",
        "sample_type": "Antibody",
        "sample_key": "anti_myc"
      }
    ]
  }
}
```
If `provision` step is present, then Menagerie will look for all of the samples listed in the Aquarium database. These can then be accessed in later steps using the `sample_key` attribute.

In subsequent steps, the `operator` contains an array of `transformations`. The `source` and `destination` entities are referred to by the `sample_key`:
```json
{
  "id": 2,
  "name": "Round 1: low concentration",
  "type": "yeast_display_round",
  "operator": {
    "transformations": [
      {
        "destination": [
          {
            "sample_key": "library_expressing"
          }
        ],
        "source": [
          {
            "sample_key": "library"
          },
          {
            "concentration": 0,
            "sample_key": "trypsin"
          },
          {
            "sample_key": "anti_myc"
          }
        ]
      },
      {
        "destination": [
          {
            "sample_key": "library_chymotrypsin_1"
          }
        ],
        "source": [
          {
            "sample_key": "library"
          },
          {
            "concentration": 28,
            "sample_key": "chymotrypsin"
          },
          {
            "sample_key": "anti_myc"
          }
        ]
      },
      {
        "destination": [
          {
            "sample_key": "library_trypsin_1"
          }
        ],
        "source": [
          {
            "sample_key": "library"
          },
          {
            "concentration": 28,
            "sample_key": "trypsin"
          },
          {
            "sample_key": "anti_myc"
          }
        ]
      },
      {
        "destination": [
          {
            "sample_key": "autofluorescence_control"
          }
        ],
        "source": [
          {
            "sample_key": "binding_negative"
          },
          {
            "concentration": 0,
            "sample_key": "trypsin"
          },
          {
            "sample_key": "anti_myc"
          }
        ]
      }
    ]
  }
}
```

