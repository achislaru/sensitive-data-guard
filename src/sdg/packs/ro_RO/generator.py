"""Deterministic synthetic-data generator for the ro_RO pack.

Produces fictitious but structurally valid data (correct CNP/IBAN/CUI check
digits) plus ground-truth PII lists, for machine self-test and protocol
dry-runs. Same seed => identical output. Contains ZERO real PII; emails use
the @exemplu-fictiv.ro domain.
"""
import csv
import io
import json
import random
from pathlib import Path

from .validators import cnp_valid  # noqa: F401  (kept for parity/debugging)

FIRST_F = ["Maria", "Andreea", "Elena", "Ioana", "Cristina", "Gabriela",
           "Ștefania", "Mihaela", "Alina", "Roxana", "Bianca", "Larisa"]
FIRST_M = ["Ion", "Andrei", "Mihai", "Ștefan", "Ionuț", "Cătălin",
           "Bogdan", "Vlad", "Radu", "Cosmin", "Dragoș", "Sorin"]
LAST = ["Popescu", "Ionescu", "Mureșan", "Călinescu", "Pârvu", "Dumitrescu",
        "Stanciu", "Georgescu", "Tănase", "Crețu", "Albu", "Văduva",
        "Iordache", "Nistor", "Bălan", "Drăgan", "Olteanu", "Fărcaș",
        "Lungu", "Apostol", "Vișan", "Țurcanu"]
CITIES = [("București", "Sector 3"), ("Cluj-Napoca", "jud. Cluj"),
          ("Iași", "jud. Iași"), ("Timișoara", "jud. Timiș"),
          ("Brașov", "jud. Brașov"), ("Constanța", "jud. Constanța")]
STREETS = ["Str. Lalelelor", "Bd. Unirii", "Str. Mihai Eminescu",
           "Calea Victoriei", "Str. Avram Iancu", "Aleea Castanilor"]
ROLES = ["Contabil senior", "Specialist HR", "Analist financiar",
         "Asistent manager", "Inginer software", "Specialist achiziții",
         "Consilier juridic", "Economist", "Referent resurse umane",
         "Administrator sistem"]
BANKS = ["BTRL", "BRDE", "RNCB", "INGB", "RZBR", "UGBI"]
EMPLOYERS = ["SC Delta Construct SRL", "SC Optimus Retail SRL",
             "SC Veridia Consulting SRL", "SC Helix Logistics SRL",
             "SC Arcadia Soft SRL", "SC Meridian Finance SRL"]


def _cnp_control(d12: str) -> str:
    s = sum(int(a) * int(b) for a, b in zip(d12, "279146358279"))
    c = s % 11
    return str(1 if c == 10 else c)


def _make_cnp(rng: random.Random, female: bool) -> str:
    year = rng.randint(1975, 2002)
    if year < 2000:
        s, yy = ("2" if female else "1"), year - 1900
    else:
        s, yy = ("6" if female else "5"), year - 2000
    month, day = rng.randint(1, 12), rng.randint(1, 28)
    county = rng.choice(list(range(1, 47)) + [51, 52])
    nnn = rng.randint(1, 999)
    d12 = f"{s}{yy:02d}{month:02d}{day:02d}{county:02d}{nnn:03d}"
    return d12 + _cnp_control(d12)


def _iban_mod97(s: str) -> int:
    return int("".join(str(int(ch, 36)) for ch in s)) % 97


def _make_iban(rng: random.Random) -> str:
    bank = rng.choice(BANKS)
    acct = "".join(rng.choice("0123456789") for _ in range(16))
    bban = bank + acct
    check = 98 - _iban_mod97(bban + "RO00")
    return f"RO{check:02d}{bban}"


def _cui_control(digits: str) -> str:
    s = sum(int(a) * int(b) for a, b in zip(digits.zfill(9), "753217532"))
    c = (s * 10) % 11
    return str(0 if c == 10 else c)


def _make_cui(rng: random.Random) -> str:
    body = str(rng.randint(100000, 9999999))
    return body + _cui_control(body)


def _make_phone(rng: random.Random) -> str:
    return "07" + "".join(rng.choice("0123456789") for _ in range(8))


def _make_email(first: str, last: str) -> str:
    t = str.maketrans("ășțâîĂȘȚÂÎ", "astaiASTAI")
    return f"{first.translate(t).lower()}.{last.translate(t).lower()}@exemplu-fictiv.ro"


def _person(rng: random.Random) -> dict:
    female = rng.random() < 0.5
    first = rng.choice(FIRST_F if female else FIRST_M)
    last = rng.choice(LAST)
    city, county = rng.choice(CITIES)
    cnp = _make_cnp(rng, female)
    return {
        "name": f"{first} {last}",
        "cnp": cnp,
        "email": _make_email(first, last),
        "phone": _make_phone(rng),
        "address": f"{rng.choice(STREETS)} nr. {rng.randint(1, 120)}, {city}, {county}",
        "iban": _make_iban(rng),
        "birth": f"{cnp[5:7]}.{cnp[3:5]}.{(1900 if cnp[0] in '12' else 2000) + int(cnp[1:3])}",
    }


CV_TEMPLATE = """CURRICULUM VITAE

Date personale
Nume și prenume: {name}
{cnp_line}Email: {email}
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
UNIS = ["Universitatea București", "UBB Cluj-Napoca", "ASE București",
        "Universitatea Al. I. Cuza Iași", "Politehnica Timișoara"]
SKILLS = ["Excel avansat", "SAP", "contabilitate primară", "salarizare Revisal",
          "legislația muncii", "raportare financiară", "Power BI",
          "recrutare și selecție", "evaluare performanță", "audit intern"]


def _gen_cv(rng: random.Random, idx: int):
    p = _person(rng)
    include_cnp = idx in (2, 5, 8)
    salary = rng.randint(4, 12) * 500
    text = CV_TEMPLATE.format(
        name=p["name"], cnp_line=f"CNP: {p['cnp']}\n" if include_cnp else "",
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
    if include_cnp:
        pii.append({"type": "CNP", "value": p["cnp"]})
    return text, pii


INVOICE_TEMPLATE = """FACTURĂ FISCALĂ
Seria NCX nr. {number} din {date}

FURNIZOR:
{supplier}
CUI: RO{cui_s}
IBAN: {iban} — {bank}

CUMPĂRĂTOR:
SC Nova Cortex Demo SRL
CUI: RO{cui_b}

Persoană de contact: {contact}, tel. {phone}, {email}

{lines}
----------------------------------------------
Total fără TVA:        {subtotal:.2f} lei
TVA 19%:               {tva:.2f} lei
TOTAL DE PLATĂ:        {total:.2f} lei

Întocmit de: {issued_by}
"""
SERVICES = [("Consultanță financiară", 250), ("Mentenanță software", 180),
            ("Salarizare externalizată", 95), ("Audit conformitate", 320),
            ("Licență software", 410), ("Curierat", 35), ("Materiale birou", 22)]
BANK_NAMES = {"BTRL": "Banca Transilvania", "BRDE": "BRD", "RNCB": "BCR",
              "INGB": "ING Bank", "RZBR": "Raiffeisen", "UGBI": "Garanti"}


def _gen_invoice(rng: random.Random, idx: int):
    supplier = rng.choice(EMPLOYERS)
    cui_s, cui_b = _make_cui(rng), _make_cui(rng)
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
    tva = subtotal * 0.19
    text = INVOICE_TEMPLATE.format(
        number=1000 + idx, date=f"{rng.randint(1,28):02d}.0{rng.randint(1,5)}.2026",
        supplier=supplier, cui_s=cui_s, cui_b=cui_b, iban=iban,
        bank=BANK_NAMES[iban[4:8]], contact=contact["name"], phone=contact["phone"],
        email=contact["email"], lines="\n".join(lines),
        subtotal=subtotal, tva=tva, total=subtotal + tva, issued_by=issued_by)
    pii = [
        {"type": "CUI", "value": f"RO{cui_s}"},
        {"type": "CUI", "value": f"RO{cui_b}"},
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
    w.writerow(["Nr", "Nume complet", "CNP", "Funcție", "Salariu brut (lei)",
                "Salariu net (lei)", "IBAN", "Email"])
    pii = []
    for i in range(1, 21):
        p = _person(rng)
        brut = rng.randint(8, 30) * 500
        net = round(brut * 0.585)
        w.writerow([i, p["name"], p["cnp"], rng.choice(ROLES), brut, net,
                    p["iban"], p["email"]])
        pii += [
            {"type": "NAME", "value": p["name"]},
            {"type": "CNP", "value": p["cnp"]},
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
