"""Attack dispatch — translates per-attack calling conventions."""


def dispatch_attack(
    attack_name, attack_fn, model, device, data_loader, eps, config_overrides
):
    """Call the appropriate attack wrapper with the correct signature."""
    if attack_name == "smoo":
        cfg = {"eps": int(eps) if eps >= 1 else int(eps * 1024)}
        cfg.update(config_overrides)
        return attack_fn(model, device, data_loader, cfg)

    elif attack_name == "adba":
        cfg = {"epsilon": eps}
        cfg.update(config_overrides)
        return attack_fn(model, device, data_loader, cfg)

    elif attack_name == "surfree":
        cfg = {"l2_threshold": eps}
        cfg.update(config_overrides)
        result = attack_fn(model, device, data_loader, cfg)
        if isinstance(result, tuple):
            return result[0]
        return result

    elif attack_name == "rays":
        query_limit = config_overrides["query_limit"]
        return attack_fn(device, model, eps, query_limit, data_loader)

    else:
        raise ValueError(f"No dispatch logic for attack '{attack_name}'")
