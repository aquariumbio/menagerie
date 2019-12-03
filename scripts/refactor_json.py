import json


file_path = "cloning_plans/test_gibson/aquarium_defaults.json"
new_file_path = "cloning_plans/test_gibson/new_aquarium_defaults.json"

with open(file_path) as f:
    old_json = json.load(f)

print(old_json)

keys = []
for od in old_json['operation_defaults']:
    for io in ['input', 'output']:
        io_defaults = od.get(io, {})
        for k1,v1 in io_defaults.items():
            for handle in ['sample', 'object_type', 'value']:
                this_data = v1.get(handle)
                if not this_data: continue
                new_data = []
                if isinstance(this_data, dict):
                    for k2,v2 in this_data.items():
                        nd = {
                            "name": v2,
                            "option_key": k2
                        }
                        new_data.append(nd)
                elif isinstance(this_data, str):
                    key = "value" if handle == "value" else "name"
                    nd = {
                        key: this_data
                    }
                    new_data.append(nd)

                v1[handle] = new_data

print(old_json)

with open(new_file_path, "w") as f:
    json.dump(old_json, f, sort_keys=True, indent=2)