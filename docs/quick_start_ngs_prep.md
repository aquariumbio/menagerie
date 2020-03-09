## Quick Start: Amplicon NGS Prep

This section describes the steps for planning NGS prep by qPCR amplification of a yeast library. It is based on methods from Gabe Rocklin's [massively parallel measurement of protein stability](https://www.ncbi.nlm.nih.gov/pubmed/28706065), but should work for any yeast library expressed from a plasmid. 

It is best to run this initially on a local Dockerized instance of Aquarium. If you haven't done so already, you can find steps for installing a Dockerized Aquarium instance [here](https://www.docker.com/get-started).

You will need to download and install three workflow libraries. You can find instructions for installing workflows [here](https://www.aquarium.bio/?category=Community&content=Importing). It is a good idea to backup the database before importing, using the script [`hot_swap_db.py`](https://github.com/dvnstrcklnd/aq-hot-swap-db). The libraries are:

* [Standard Libraries](https://github.com/klavinslab/standard-libraries)
* [PCR Models](https://github.com/dvnstrcklnd/aq-pcr-models)
* [Sample Models](https://github.com/dvnstrcklnd/aq-sample-models)
* [Amplicon NGS Prep](https://github.com/dvnstrcklnd/aq-amplicon-ngs-prep)

It is also a good idea to back up the database (using a distinct file name) after importing these. 

Next, you will need to populate the database with some `Samples`. To do this, open the VS Code terminal using `^~` and run 

```bash
python util/load_test_samples.py -f ngs_prep_test_samples.json
```

From the browser, you should see that the following `Samples` are loaded:
```
►	7: P7-finish_TSBC03-r		
►	6: P7-finish_TSBC02-r		
►	5: P7-finish_TSBC01-r		
►	4: Petcon NGS prep forward primer		
►	3: Petcon Reverse		
►	2: Petcon Forward		
►	1: DNA LIBRARY SAMPLE NAME
```

You can again back up the database (using a third distinct file name) after creating these.

Next, from the VS Code terminal, run: 
```bash
vscode@docker-desktop:/workspaces/menagerie$ python plan_ngs_prep.py -t
```
Which produces the output:
```bash
RUNNING IN TEST MODE
Connected to Aquarium at http://localhost/ using pydent version 0.0.35
Logged in as Joe Neptune

Set IO for Treat With Zymolyase
Set IO for Yeast Plasmid Extraction
Set IO for Digest Genomic DNA
### 3 total operations

Set IO for Make qPCR Fragment
Set IO for Run Pre-poured Gel
Set IO for Extract Gel Slice (NGS)
Set IO for Purify Gel Slice (NGS)
### 7 total operations

Set IO for Make qPCR Fragment WITH PLATES
Set IO for Run Pre-poured Gel
Set IO for Extract Gel Slice (NGS)
Set IO for Purify Gel Slice (NGS)
### 11 total operations

Set IO for Qubit concentration
Set IO for Dilute to 4nM
### 13 total operations
.
.
.
Created Plan: http://localhost//plans?plan_id=1
39 total operations.
36 total wires.
```

You may also see warnings like these near the beginning of the output:
```
WARNING: Sample not found: SDO -His -Trp -Ura
WARNING: ObjectType not found: Yeast Library Glycerol Stock
```
This is probably fine as it is likely the result of the software looking for `Samples` and `ObjectTypes` listed in `aquarium_defaults.json` that are not in the minimal database that has been set up.

To view the plan, click on the link provided at the end of the output. You should see something like this:
<img src="./docs/_images/quick_start_ngs_prep.png" alt="NGS Prep Plan" width="800"/>

Note that the `Plan` will not be ready to launch, because there are no `Items` in the Aquarium inventory.