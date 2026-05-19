"""Attack dispatch — translates per-attack calling conventions."""


def dispatch_attack(
    attack_name, attack_fn, model, device, data_loader, eps, config_overrides
):
    """Call the appropriate attack wrapper with the right signature.

    Each attack has its own calling convention. This function maps
    the unified (attack_name, eps, config_overrides) interface to the
    specific argument layout each wrapper expects.
    """

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
        # SurFree returns (advLoader, adv_blobs) — extract the loader
        if isinstance(result, tuple):
            return result[0]
        return result

    elif attack_name == "rays":
        query_limit = config_overrides["query_limit"]
        return attack_fn(device, model, eps, query_limit, data_loader)

    elif attack_name in ("l0_pgd", "l0_sigma_pgd", "l0_linf_pgd"):
        sparsity = int(eps) if eps >= 1 else int(eps * 1024)
        n_restarts = config_overrides["n_restarts"]
        num_steps = config_overrides["num_steps"]
        step_size = config_overrides["step_size"]
        random_start = config_overrides["random_start"]
        return attack_fn(
            model,
            device,
            data_loader,
            n_restarts,
            num_steps,
            step_size,
            sparsity,
            random_start,
        )

    else:
        raise ValueError(f"No dispatch logic for attack '{attack_name}'")
