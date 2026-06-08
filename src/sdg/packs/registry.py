"""Country-pack discovery. Packs are subpackages of sdg.packs exporting PACK."""
import importlib
import pkgutil

from .base import CountryPack


def available_locales() -> list[str]:
    import sdg.packs as pkgs
    out = []
    for mod in pkgutil.iter_modules(pkgs.__path__):
        if mod.ispkg:
            out.append(mod.name)
    return sorted(out)


def load_pack(locale: str) -> CountryPack:
    try:
        mod = importlib.import_module(f"sdg.packs.{locale}")
    except ModuleNotFoundError as e:
        raise ValueError(f"unknown locale pack: {locale}") from e
    pack = getattr(mod, "PACK", None)
    if not isinstance(pack, CountryPack):
        raise ValueError(f"pack {locale} does not export a CountryPack PACK")
    return pack
