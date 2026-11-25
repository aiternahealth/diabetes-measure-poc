"""Layer L1: run the SQL-on-FHIR ViewDefinitions over the exported NDJSON and load typed tables into DuckDB.

  engine=pathling   (default) Pathling 10 / Spark 4 — needs Java 17+, downloads its engine jar on first run
  engine=mini       small pure-Python runner (fhirpathpy) — fine for a few thousand patients, no Java

Output: DuckDB schema fhir_views in data/dcg.duckdb (one table per view) + Parquet copies in data/views/.
Usage: python etl/run_views.py [--engine pathling|mini] [--ndjson data/ndjson]
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, DCG  # noqa: E402

DUCKDB_TYPES = {"date": "DATE", "dateTime": "TIMESTAMP", "instant": "TIMESTAMP", "decimal": "DOUBLE",
                "integer": "BIGINT", "boolean": "BOOLEAN"}


def columns(view):
    out = []

    def walk(selects):
        for s in selects:
            out.extend((c["name"], c.get("type", "string")) for c in s.get("column", []))
            walk(s.get("select", []))
            walk(s.get("unionAll", []))
    walk(view["select"])
    return out


def to_timestamp(series):
    s = series.astype("string")
    s = s.where(s.str.len() != 4, s + "-01-01").where(s.str.len() != 7, s + "-01")   # FHIR partial dates
    return pd.to_datetime(s, utc=True, errors="coerce", format="ISO8601").dt.tz_convert(None)


def normalise(df, cols):
    for name, typ in cols:
        if name not in df:
            df[name] = None
        if typ in ("date", "dateTime", "instant"):
            ts = to_timestamp(df[name])
            df[name] = ts.dt.date if typ == "date" else ts
        elif typ in ("decimal", "integer"):
            df[name] = pd.to_numeric(df[name], errors="coerce")
        elif typ == "boolean":
            df[name] = df[name].map(lambda v: None if v is None or pd.isna(v) else str(v).lower() == "true")
        else:
            df[name] = df[name].astype("string")
    return df[[n for n, _ in cols]]


def run_pathling(views, ndjson_dir):
    from pathling import PathlingContext
    pc = PathlingContext.create()
    data = pc.read.ndjson(str(ndjson_dir))
    present = {p.name.split(".")[0] for p in Path(ndjson_dir).glob("*.ndjson")}
    for v in views:
        if v["resource"] not in present:
            yield v, pd.DataFrame()
            continue
        yield v, data.view(json=json.dumps(v)).toPandas()


def run_mini(views, ndjson_dir):
    from sof_mini import run_view
    cache = {}
    for v in views:
        t = v["resource"]
        if t not in cache:
            f = Path(ndjson_dir) / f"{t}.ndjson"
            cache[t] = [json.loads(line) for line in f.open()] if f.exists() else []
        yield v, pd.DataFrame(run_view(v, cache[t]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=["pathling", "mini"], default="pathling")
    ap.add_argument("--ndjson", default=str(DATA / "ndjson"))
    ap.add_argument("--db", default=str(DATA / "dcg.duckdb"))
    args = ap.parse_args()
    views = [json.load(open(f)) for f in sorted((DCG / "views").glob("*.json"))]
    (DATA / "views").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists fhir_views")
    runner = run_pathling if args.engine == "pathling" else run_mini
    for v, df in runner(views, args.ndjson):
        cols = columns(v)
        df = normalise(df, cols)
        con.register("df_in", df)
        ddl = ", ".join(f'cast("{n}" as {DUCKDB_TYPES.get(t, "VARCHAR")}) as "{n}"' for n, t in cols)
        con.execute(f'create or replace table fhir_views.{v["name"]} as select {ddl} from df_in')
        con.unregister("df_in")
        con.execute(f"copy fhir_views.{v['name']} to '{DATA / 'views' / (v['name'] + '.parquet')}' (format parquet)")
        print(f"  {v['name']:26s} {len(df):>9,} rows")
    con.close()
    print(f"Loaded views into {args.db} (schema fhir_views)")


if __name__ == "__main__":
    main()
