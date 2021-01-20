def recursive_update_dict(d1: dict, d2: dict) -> None:
    """Recursively update environ input (or pw input) type data

    Args:
        d1 (dict): The dictionary to be updated
        d2 (dict): The dictionary to add to the updated
    """
    for k1 in d1:
        for k2 in d2:
            if k2 not in d1:
                d1[k2] = d2[k2]
            elif k2 == k1:
                d1[k1].update(d2[k2])
