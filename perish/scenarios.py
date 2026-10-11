"""Scenario variants of a case (used for robustness and for the twin-ready demonstration)."""
import copy


def surprise(case, intake=1.25, pack_rate=0.85):
    """'The season surprised us': more fruit than planned, slower packing than assumed."""
    c = copy.deepcopy(case)
    c.total_intake_t *= intake
    for s in c.stages:
        if s["var"] == "n_pack":
            s["rate"] *= pack_rate
    c.name += f" [intake x{intake}, pack rate x{pack_rate}]"
    return c
