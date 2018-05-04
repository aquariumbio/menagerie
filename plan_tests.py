import json
import re

def test_plan(plan, out_path, ref_path):
    p_dump = plan.aq_plan.dump(all_relations=True)
    plan_out = json.dumps(p_dump, indent=4, sort_keys=True)

    with open(out_path, 'w') as f:
        f.write(plan_out)

    with open(out_path, 'r') as f:
        plan_out = str(json.load(f))

    with open(ref_path, 'r') as f:
        plan_ref = str(json.load(f))

    assert remove_incidentals(plan_out) == remove_incidentals(plan_ref)


def remove_incidentals(plan_json):
    keys = [
        "rid",
        "id",
        "created_at",
        "updated_at",
        "operation_id",
        "plan_id",
        "from_id",
        "to_id"
    ]

    for k in keys:
        pat = r'(?<=("|\')' + re.escape(k) + r'("|\'): ).+'
        plan_json = re.sub(pat, '0', plan_json)

    return plan_json
