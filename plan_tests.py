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

    # print(remove_gids(plan_out))
    # print()
    # print(remove_gids(plan_ref))

    assert remove_gids(plan_out) == remove_gids(plan_ref)


def remove_gids(plan_json):
    return re.sub(r'(?<=("|\')rid("|\'): )\d+', '0', plan_json)
