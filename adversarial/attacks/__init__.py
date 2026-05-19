# Attack registry — maps attack name strings to wrapper callables.
# Each wrapper has its own signature; the pipeline handles dispatch.

def _lazy_smoo():
    from .SMOO_attack import SMOO_AttackWrapper
    return SMOO_AttackWrapper

def _lazy_adba():
    from .adba_attack import ADBA_AttackWrapper
    return ADBA_AttackWrapper

def _lazy_surfree():
    from .surfree_attack import SurFree_AttackWrapper
    return SurFree_AttackWrapper

def _lazy_rays():
    from .rays_attack import RaySAttack
    return RaySAttack

def _lazy_l0_pgd():
    from .l0_attack import L0_PGD_AttackWrapper
    return L0_PGD_AttackWrapper

def _lazy_l0_sigma_pgd():
    from .l0_attack import L0_Sigma_PGD_AttackWrapper
    return L0_Sigma_PGD_AttackWrapper

def _lazy_l0_linf_pgd():
    from .l0_attack import L0_Linf_PGD_AttackWrapper
    return L0_Linf_PGD_AttackWrapper


ATTACK_REGISTRY = {
    "smoo": _lazy_smoo,
    "adba": _lazy_adba,
    "surfree": _lazy_surfree,
    "rays": _lazy_rays,
    "l0_pgd": _lazy_l0_pgd,
    "l0_sigma_pgd": _lazy_l0_sigma_pgd,
    "l0_linf_pgd": _lazy_l0_linf_pgd,
}


def get_attack(name):
    if name not in ATTACK_REGISTRY:
        raise ValueError(f"Unknown attack '{name}'. Available: {list(ATTACK_REGISTRY)}")
    return ATTACK_REGISTRY[name]()
