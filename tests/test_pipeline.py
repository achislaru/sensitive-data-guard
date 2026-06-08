"""F1/F5: pseudonymization round-trip + fail-closed outbound guard."""
import pytest

from sdg.pipeline import OutboundPiiError, pseudonymize
from sdg.packs.registry import load_pack
from sdg.vault import Vault


@pytest.fixture
def vault(tmp_path):
    pack = load_pack("ro_RO")
    return Vault(db=tmp_path / "v.db", key=tmp_path / "v.key",
                 label_map=pack.label_map)


def test_roundtrip_restores_identity(vault):
    # CNP and IBAN below are structurally valid (correct check digits).
    text = ("Angajata Maria Popescu, CNP 2850512123456, "
            "cont RO66RNCB0082005630840000, maria.popescu@firma.ro, 0722123456.")
    pseudo = pseudonymize(text, vault, locale="ro_RO")
    # critical PII is gone from the outbound text
    assert "2850512123456" not in pseudo
    assert "RO66RNCB0082005630840000" not in pseudo
    assert "maria.popescu@firma.ro" not in pseudo
    # restoring brings the real values back
    restored = vault.restore(pseudo)
    assert "2850512123456" in restored
    assert "RO66RNCB0082005630840000" in restored
    assert "maria.popescu@firma.ro" in restored


def test_fail_closed_on_residual_pii(vault, monkeypatch):
    """If pseudonymization somehow leaves a valid CNP, the guard MUST raise.

    We simulate a buggy/poisoned run by neutering the pseudonym step so the
    CNP survives into the outbound text; the re-scan must catch it.
    """
    import sdg.pipeline as pipe

    # make pseudonym() a no-op so the CNP stays in place
    monkeypatch.setattr(vault, "pseudonym", lambda value, etype: value)
    with pytest.raises(OutboundPiiError):
        pipe.pseudonymize("CNP 2850512123456 rămâne în text", vault, locale="ro_RO")
