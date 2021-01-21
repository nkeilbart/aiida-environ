def recursive_update_dict(d1: dict, d2: dict) -> None:
    """Recursively update environ input (or pw input) type data

    Args:
        d1 (dict): The dictionary to be updated
        d2 (dict): The dictionary to add to the updated
    """
    for k in d2:
        if k not in d1:
            d1[k] = d2[k]
    for k in d1:
        if k in d2:
            d1[k].update(d2[k])
