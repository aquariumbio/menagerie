# ext-plan-pydent
Code to generate Aquarium plans from external planners such as XPlan and Puppeteer

## Setup
In order to login to Aquarium, you'll need to add a file `config.yml` to the top level that looks like this:
```
---
aquarium:
  nursery:
    username: "your_username"
    password: "your_password"
    url: "nursery_uri"
  production:
    username: "your_username"
    password: "your_password"
    url: "production_uri"
```
