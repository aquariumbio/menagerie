import json
import argparse

from pydent import models
from pydent.models import Sample, Item

from util.pydent_helper import create_session, prettyprint

def load_test_samples(sample_file, aq_instance="laptop"):
    session = create_session(aq_instance)

    with open(sample_file, "r") as f:
        data = json.load(f)

    sample_data = data.get("samples")
    if sample_data:
        load_samples(sample_data, session)

    item_data = data.get("items")
    if item_data:
        create_items(item_data, session)

def load_samples(sample_data, session):
    new_samples = []
    for s in sample_data:
        st_name = s.pop("sample_type")
        sample_type = session.SampleType.find_by_name(st_name)
        s["sample_type_id"] = sample_type.id

        if session.Sample.find_by_name(s["name"]):
            print("Found Sample: {}".format(s["name"]))
        else:
            new_sample = session.Sample.new(**s)
            new_sample.save()
            new_samples.append(new_sample)

    if new_samples: print("Loaded {} Samples:".format(len(new_samples)))
    for s in new_samples:
        print(s.name)

    return new_samples

def create_items(item_data, session):
    new_items = []
    new_collections = []
    for i in item_data:
        s = session.Sample.find_by_name(i["sample"])
        ot = session.ObjectType.find_by_name(i["object_type"])
        if ot.handler == "collection":
            collection = next(iter([c for c in new_collections if c.object_type.name == ot.name]), None)
            empties = get_empties(collection)
            if not empties:
                collection = session.Collection.new(object_type = ot)
                collection.save()
                new_collections.append(collection)
                empties = get_empties(collection)
            e = empties.pop(0)
            collection[e[0], e[1]] = s
            new_item = collection.part_matrix[e[0], e[1]]
            collection.save()
        else:
            new_item = session.Item.new(sample_id=s.id, object_type_id=ot.id)

        new_item.save()
        new_items.append(new_item)

    print("Created {} Items:".format(len(new_items)))
    for i in new_items:
        print("{}: {} in {}".format(i.id, i.sample.name, i.object_type.name))

    return new_items

def get_empties(collection):
    empties = []
    if not collection: return
    for r, row in enumerate(collection.matrix):
        for c, cell in enumerate(row):
            if not cell:
                empties.append([r, c])
    return empties

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename",
                        help="name of json file in test_samples folder")
    return parser.parse_args()

def main():
    args = get_args()
    load_test_samples(args.filename)

if __name__ == "__main__":
    main()