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

