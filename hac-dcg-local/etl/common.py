"""Shared helpers: settings from .env, Medplum client-credentials auth, value-set seeds."""
import csv
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent          # hac-dcg-local/
DCG = ROOT / "dcg"                                      # semantic-model package
DATA = ROOT / "data"


def load_env():
    """Minimal .env reader (KEY=VALUE lines); real environment variables win."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
BASE_URL = os.environ.get("MEDPLUM_BASE_URL", "http://localhost:8103/").rstrip("/") + "/"
FHIR = BASE_URL + "fhir/R4/"


class Medplum:
    """Tiny Medplum client using the OAuth2 client-credentials grant (a ClientApplication)."""

    def __init__(self):
        self.client_id = os.environ.get("MEDPLUM_CLIENT_ID")
        self.client_secret = os.environ.get("MEDPLUM_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise SystemExit("Set MEDPLUM_CLIENT_ID and MEDPLUM_CLIENT_SECRET in .env (see README step 3).")
        self.session = requests.Session()
        self._token, self._expires = None, 0

    def token(self):
        if not self._token or time.time() > self._expires - 60:
            r = requests.post(BASE_URL + "oauth2/token", data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }, timeout=30)
            if r.status_code != 200:
                raise SystemExit(f"Token request failed ({r.status_code}): {r.text[:300]}")
            body = r.json()
            self._token, self._expires = body["access_token"], time.time() + int(body.get("expires_in", 3600))
        return self._token

    def headers(self, extra=None):
        h = {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/fhir+json",
             "Accept": "application/fhir+json"}
        h.update(extra or {})
        return h

    def request(self, method, path_or_url, **kw):
        url = path_or_url if path_or_url.startswith("http") else FHIR + path_or_url.lstrip("/")
        extra = kw.pop("headers", None)
        for attempt in range(4):
            r = self.session.request(method, url, headers=self.headers(extra), timeout=kw.pop("timeout", 300), **kw)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return r
        return r


def value_sets():
    """{(system, code): {value_set, ...}} from the ontology-generated seed."""
    out = {}
    for row in csv.DictReader(open(DCG / "seeds" / "seed_code_valueset.csv")):
        out.setdefault((row["code_system"], row["code"]), set()).add(row["value_set"])
    return out


def medication_classes():
    """[(ingredient_keyword, therapy_class, atc_code)] from the medication seed: each keyword row, with the
    shortest ATC prefix of its class (used to add an ATC coding to Synthea's RxNorm-only orders)."""
    rows = list(csv.DictReader(open(DCG / "seeds" / "seed_medication_class.csv")))
    atc = {}
    for r in rows:
        if r["match_kind"] == "atc" and (r["therapy_class"] not in atc or len(r["pattern"]) < len(atc[r["therapy_class"]])):
            atc[r["therapy_class"]] = r["pattern"]
    return [(r["pattern"], r["therapy_class"], atc.get(r["therapy_class"], "")) for r in rows if r["match_kind"] == "keyword"]


def value_set_match(system, code, vs_index):
    """Value sets for a code, honouring ICD-10-CA prefix rows (a code matches its parent's rows)."""
    out = set(vs_index.get((system, code), set()))
    if system.endswith("icd10ca") and code:
        c = code.replace(".", "")
        for (sys_, prefix), sets in vs_index.items():
            if sys_ == system and c.startswith(prefix.replace(".", "")):
                out |= sets
    return out
