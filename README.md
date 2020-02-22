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

## Using Menagerie

Menagerie uses several classes to manage the conversion of a JSON-formatted plan into an Aquarium `Plan` object.

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
        },"Yeast Culture": {
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
            "destination":  [
                {
                    "sample_key": "library_expressing"
                }
            ],
            "source":  [
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
            "destination":  [
							{
								"sample_key": "library_chymotrypsin_1"
							}
						],
            "source":  [
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
            "destination":  [
							{
								"sample_key": "library_trypsin_1"
							}
						],
            "source":  [
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
            "destination":  [
							{
								"sample_key": "autofluorescence_control"
							}
						],
            "source":  [
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

### Plan a protein stability experiment
From `plan_protein_stability.py`
```python
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from util.plans import Cursor
from util.yeast_display_plans import YeastDisplayPlan
from util.user_input import get_input

# Ask for inputs on the command line
inputs = get_input()

# Override get_input() for convenience when testing code
# inputs = {
#     'plan_path': 'yeast_display_plans/template_stability', 
#     'start_date': datetime.today(), 
#     'aq_instance': 'laptop'
# }

start_date = inputs['start_date']
plan = YeastDisplayPlan(inputs['plan_path'], inputs['aq_instance'])

# Keeps track of where to put the next operation in the Aquarium Designer GUI
cursor = Cursor(y=18)

# The `plan.py` file may contain other types of steps, but we only
#   want the `yeast_display_round` steps
for plan_step in plan.get_steps_by_type('yeast_display_round'):
    plan_step.create_step(cursor, start_date)

    # Schedule certain operations on M, W, F
    if start_date.weekday() == 4:
        incr = 3
    else:
        incr = 2

    start_date += timedelta(days=incr)

    plan_step.report()

plan.create_aq_plan()
plan.add_data_associations()
plan.report()
```