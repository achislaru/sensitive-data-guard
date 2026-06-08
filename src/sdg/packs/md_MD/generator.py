"""Deterministic synthetic-data generator for the md_MD pack.

Produces fictitious but structurally valid Moldovan data (correct IDNP/IDNO/
IBAN-MD check digits) plus ground-truth PII lists, for machine self-test and
protocol dry-runs. Same seed => identical output. Contains ZERO real PII; emails
use the @exemplu-fictiv.md domain.
"""
import csv
import io
import json
import random
from pathlib import Path

from .validators import _WEIGHTS

FIRST_F = ["Maria", "Ana", "Elena", "Cristina", "Doina", "Natalia",
           "Victoria", "Mihaela", "Lilia", "Tatiana", "Olga", "Veronica"]
FIRST_M = ["Ion", "Andrei", "Mihai", "Vasile", "Sergiu", "Veaceslav",
           "Dumitru", "Vlad", "Radu", "Nicolae", "Grigore", "Petru"]
LAST = ["Rusu", "Ciobanu", "Popa", "Munteanu", "Cojocaru", "Lungu",
        "Moraru", "Cebotari", "Rotaru", "Bivol", "Ursu", "Gangan",
        "Sîrbu", "Țurcanu", "Grosu", "Bejan", "Damaschin", "Verejan",
        "Iurcu", "Postică", "Guțu", "Spătaru"]
CITIES = [("Chișinău", "mun. Chișinău"), ("Bălți", "mun. Bălți"),
          ("Cahul", "r-nul Cahul"), ("Orhei", "r-nul Orhei"),
          ("Ungheni", "r-nul Ungheni"), ("Soroca", "r-nul Soroca")]
STREETS = ["str. Ștefan cel Mare", "bd. Dacia", "str. Mihai Eminescu",
           "str. Alexandru cel Bun", "str. Vasile Alecsandri", "str. Ismail"]
ROLES = ["Contabil-șef", "Specialist resurse umane", "Analist financiar",
         "Asistent manager", "Inginer software", "Specialist achiziții",
         "Consilier juridic", "Economist", "Referent", "Administrator de sistem"]
EMPLOYERS = ["SRL Codru Construct", "SRL Optimus Retail", "SRL Veridia Consulting",
             "SRL Helix Logistic", "SRL Arcadia Soft", "SRL Meridian Finanțe"]


def _idn_control(d12: str) -> str:
    s = sum(int(a) * w for a, w in zip(d12, _WEIGHTS))
    return str(s % 10)


def _make_idnp(rng: random.Random) -> str:
    # IDNP for persons commonly starts with 0 or 2; the checksum is what matters
    d12 = str(rng.choice([0, 2])) + "".join(rng.choice("0123456789") for _ in range(11))
    return d12 + _idn_control(d12)


def _make_idno(rng: random.Random) -> str:
    # IDNO for legal entities commonly starts with 1
    d12 = "1" + "".join(rng.choice("0123456789") for _ in range(11))
    return d12 + _idn_control(d12)


def _iban_mod97(s: str) -> int:
    return int("".join(str(int(ch, 36)) for ch in s)) % 97


def _make_iban(rng: random.Random) -> str:
    # MD BBAN = 2 alpha bank code + 18 alphanumeric (here digits)
    bank = "".join(rng.choice("ABCDEFGH") for _ in range(2))
    acct = "".join(rng.choice("0123456789") for _ in range(18))
    bban = bank + acct
    check = 98 - _iban_mod97(bban + "MD00")
    return f"MD{check:02d}{bban}"


def _make_phone(rng: random.Random) -> str:
    return "0" + rng.choice("67") + "".join(rng.choice("0123456789") for _ in range(7))


def _make_email(first: str, last: str) -> str:
    t = str.maketrans("ășțâîĂȘȚÂÎ", "astaiASTAI")
    return f"{first.translate(t).lower()}.{last.translate(t).lower()}@exemplu-fictiv.md"


def _person(rng: random.Random) -> dict:
    female = rng.random() < 0.5
    first = rng.choice(FIRST_F if female else FIRST_M)
    last = rng.choice(LAST)
    city, region = rng.choice(CITIES)
    return {
        "name": f"{first} {last}",
        "idnp": _make_idnp(rng),
        "email": _make_email(first, last),
        "phone": _make_phone(rng),
        "address": f"{rng.choice(STREETS)} nr. {rng.randint(1, 120)}, {city}, {region}",
        "iban": _make_iban(rng),
        "birth": f"{rng.randint(1,28):02d}.{rng.randint(1,12):02d}.{rng.randint(1975,2002)}",
    }


CV_TEMPLATE = """CURRICULUM VITAE

Date personale
Nume și prenume: {name}
{idnp_line}Email: {email}
Telefon: {phone}
Adresă: {address}
Data nașterii: {birth}

Obiectiv profesional
Doresc să ocup postul de {role}, valorificând experiența mea în domeniu.

Experiență profesională
• {employer} — {role2} ({y1}-{y2})

Educație
• {uni} — licență

Competențe: {skills}
Salariu așteptat: {salary} lei net/lună
"""
UNIS = ["Universitatea de Stat din Moldova", "ASEM Chișinău",
        "Universitatea Tehnică a Moldovei", "Universitatea de Stat Alecu Russo Bălți",
        "Academia de Studii Economice"]
SKILLS = ["Excel avansat", "1C Contabilitate", "contabilitate primară",
          "salarizare", "legislația muncii", "raportare financiară", "Power BI",
          "recrutare și selecție", "evaluare performanță", "audit intern"]


def _gen_cv(rng: random.Random, idx: int):
    p = _person(rng)
    include_idnp = idx in (2, 5, 8)
    salary = rng.randint(8, 25) * 1000
    text = CV_TEMPLATE.format(
        name=p["name"], idnp_line=f"IDNP: {p['idnp']}\n" if include_idnp else "",
        email=p["email"], phone=p["phone"], address=p["address"], birth=p["birth"],
        role=rng.choice(ROLES), role2=rng.choice(ROLES),
        employer=rng.choice(EMPLOYERS), y1=2014, y2=2020,
        uni=rng.choice(UNIS), skills=", ".join(rng.sample(SKILLS, 4)), salary=salary)
    pii = [
        {"type": "NAME", "value": p["name"]},
        {"type": "EMAIL", "value": p["email"]},
        {"type": "PHONE", "value": p["phone"]},
        {"type": "ADDRESS", "value": p["address"]},
        {"type": "BIRTHDATE", "value": p["birth"]},
        {"type": "SALARY", "value": f"{salary} lei"},
    ]
    if include_idnp:
        pii.append({"type": "IDNP", "value": p["idnp"]})
    return text, pii


INVOICE_TEMPLATE = """FACTURĂ FISCALĂ
Seria MD nr. {number} din {date}

FURNIZOR:
{supplier}
IDNO: {idno_s}
IBAN: {iban} — {bank}

CUMPĂRĂTOR:
SRL Nova Cortex Demo
IDNO: {idno_b}

Persoană de contact: {contact}, tel. {phone}, {email}

{lines}
----------------------------------------------
Total fără TVA:        {subtotal:.2f} lei
TVA 20%:               {tva:.2f} lei
TOTAL DE PLATĂ:        {total:.2f} lei

Întocmit de: {issued_by}
"""
SERVICES = [("Consultanță financiară", 250), ("Mentenanță software", 180),
            ("Salarizare externalizată", 95), ("Audit conformitate", 320),
            ("Licență software", 410), ("Curierat", 35), ("Materiale birou", 22)]
BANK_NAMES = ["Moldova Agroindbank", "Moldindconbank", "Victoriabank",
              "Mobiasbanca", "Eximbank", "Energbank"]


def _gen_invoice(rng: random.Random, idx: int):
    supplier = rng.choice(EMPLOYERS)
    idno_s, idno_b = _make_idno(rng), _make_idno(rng)
    iban = _make_iban(rng)
    contact = _person(rng)
    issued_by = _person(rng)["name"]
    n_lines = rng.randint(1, 3)
    lines, subtotal = [], 0.0
    for i, (svc, price) in enumerate(rng.sample(SERVICES, n_lines), 1):
        qty = rng.randint(1, 5)
        val = qty * price * rng.uniform(0.9, 1.4)
        subtotal += val
        lines.append(f"{i}. {svc} — {qty} buc x {val/qty:.2f} = {val:.2f} lei")
    tva = subtotal * 0.20
    text = INVOICE_TEMPLATE.format(
        number=1000 + idx, date=f"{rng.randint(1,28):02d}.0{rng.randint(1,5)}.2026",
        supplier=supplier, idno_s=idno_s, idno_b=idno_b, iban=iban,
        bank=rng.choice(BANK_NAMES), contact=contact["name"], phone=contact["phone"],
        email=contact["email"], lines="\n".join(lines),
        subtotal=subtotal, tva=tva, total=subtotal + tva, issued_by=issued_by)
    pii = [
        {"type": "IDNO", "value": idno_s},
        {"type": "IDNO", "value": idno_b},
        {"type": "IBAN", "value": iban},
        {"type": "NAME", "value": contact["name"]},
        {"type": "NAME", "value": issued_by},
        {"type": "PHONE", "value": contact["phone"]},
        {"type": "EMAIL", "value": contact["email"]},
        {"type": "ORG", "value": supplier},
    ]
    return text, pii


def _gen_payroll(rng: random.Random):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Nr", "Nume complet", "IDNP", "Funcție", "Salariu brut (lei)",
                "Salariu net (lei)", "IBAN", "Email"])
    pii = []
    for i in range(1, 21):
        p = _person(rng)
        brut = rng.randint(8, 30) * 1000
        net = round(brut * 0.76)
        w.writerow([i, p["name"], p["idnp"], rng.choice(ROLES), brut, net,
                    p["iban"], p["email"]])
        pii += [
            {"type": "NAME", "value": p["name"]},
            {"type": "IDNP", "value": p["idnp"]},
            {"type": "SALARY", "value": str(brut)},
            {"type": "IBAN", "value": p["iban"]},
            {"type": "EMAIL", "value": p["email"]},
        ]
    return buf.getvalue(), pii


def generate(seed: int, out_dir: Path) -> Path:
    """Write fixtures + ground truth under out_dir; return manifest path."""
    rng = random.Random(seed)
    data = out_dir / "data"
    gt = out_dir / "ground-truth"
    for sub in ("cv", "invoices", "payroll"):
        (data / sub).mkdir(parents=True, exist_ok=True)
    gt.mkdir(parents=True, exist_ok=True)

    manifest = []

    def _write(rel: str, content: str, pii: list):
        (out_dir / rel).write_text(content, encoding="utf-8")
        stem = Path(rel).stem
        (gt / f"{stem}.json").write_text(
            json.dumps({"file": rel, "pii": pii}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        manifest.append({"file": rel, "n_pii": len(pii)})

    for i in range(10):
        text, pii = _gen_cv(rng, i)
        _write(f"data/cv/cv_{i+1:02d}.txt", text, pii)
    for i in range(10):
        text, pii = _gen_invoice(rng, i)
        _write(f"data/invoices/invoice_{i+1:02d}.txt", text, pii)
    text, pii = _gen_payroll(rng)
    _write("data/payroll/payroll.csv", text, pii)

    total = sum(m["n_pii"] for m in manifest)
    manifest_path = gt / "MANIFEST.json"
    manifest_path.write_text(json.dumps(
        {"seed": seed, "files": len(manifest), "total_pii": total,
         "items": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
