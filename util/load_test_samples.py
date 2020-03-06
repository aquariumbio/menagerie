import json
import pydent
from pydent import models
from pydent.models import Sample, Item

from pydent_helper import create_session, prettyprint

def main():
    session = create_session("laptop")

    with open("yeast_display_test_samples.json", "r") as f:
        data = json.load(f)

    for s in data.get("samples", []):
        st_name = s.pop("sample_type")
        sample_type = session.SampleType.find_by_name(st_name)
        s["sample_type_id"] = sample_type.id

        new_sample = session.Sample.new(**s)
        new_sample.save()

    samples = session.Sample.all()
    print("Loaded {} Samples:".format(len(samples)))
    for s in samples:
        print(s.name)

if __name__ == "__main__":
    main()