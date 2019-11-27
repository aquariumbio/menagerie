# menagerie
Code to generate Aquarium plans from JSON files

## Setup
In order to login to Aquarium, you'll need to add a file `secrets.json` to `util` that looks like this:
```
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
