import argparse
import os
import sqlite3
import sys
from pathlib import Path


def integrity_check(db_path: Path) -> list[str]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA integrity_check;")
        return [r[0] for r in cur.fetchall()]
    finally:
        con.close()


def try_iterdump(db_path: Path, out_sql_path: Path) -> tuple[bool, str]:
    """
    Best-effort dump. Corruption may raise DatabaseError mid-stream.
    We still keep whatever was written, which can sometimes be imported partially.
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    out_sql_path.parent.mkdir(parents=True, exist_ok=True)
    wrote = 0
    try:
        with out_sql_path.open("w", encoding="utf-8") as f:
            f.write("PRAGMA foreign_keys=OFF;\n")
            f.write("BEGIN TRANSACTION;\n")
            try:
                for line in con.iterdump():
                    f.write(line)
                    if not line.endswith("\n"):
                        f.write("\n")
                    wrote += 1
            except sqlite3.DatabaseError as e:
                f.write("-- ERROR DURING DUMP:\n")
                f.write(f"-- {e}\n")
                return False, f"Dump interrompu (lignes écrites: {wrote}). Erreur: {e}"
            finally:
                f.write("COMMIT;\n")
        return True, f"Dump OK (lignes écrites: {wrote})."
    finally:
        con.close()


def import_sql(sql_path: Path, out_db_path: Path) -> tuple[bool, str]:
    if out_db_path.exists():
        out_db_path.unlink()
    con = sqlite3.connect(str(out_db_path))
    try:
        cur = con.cursor()
        sql = sql_path.read_text(encoding="utf-8", errors="replace")
        try:
            cur.executescript(sql)
            con.commit()
            return True, "Import OK."
        except sqlite3.DatabaseError as e:
            return False, f"Import partiel/échoué: {e}"
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broken-db", required=True, help="Path to broken sqlite db")
    parser.add_argument("--out-sql", default="tools/recovered_dump.sql", help="Output SQL dump path")
    parser.add_argument("--out-db", default="db_recovered.sqlite3", help="Recovered sqlite db path")
    args = parser.parse_args()

    broken = Path(args.broken_db).resolve()
    out_sql = Path(args.out_sql).resolve()
    out_db = Path(args.out_db).resolve()

    if not broken.exists():
        print(f"[ERROR] Fichier introuvable: {broken}")
        return 2

    print(f"[1/3] integrity_check sur: {broken.name}")
    try:
        rows = integrity_check(broken)
        print("  Résultat:")
        for r in rows[:20]:
            print(f"   - {r}")
        if len(rows) > 20:
            print(f"   - ... ({len(rows)} lignes)")
    except Exception as e:
        print(f"  integrity_check error: {e}")

    print(f"[2/3] Dump SQL -> {out_sql}")
    ok_dump, msg_dump = try_iterdump(broken, out_sql)
    print(f"  {msg_dump}")

    print(f"[3/3] Import SQL -> {out_db}")
    ok_imp, msg_imp = import_sql(out_sql, out_db)
    print(f"  {msg_imp}")

    if ok_dump and ok_imp:
        print("[OK] Base récupérée créée.")
        return 0

    print("[WARN] Récupération partielle. On peut tenter une récupération table-par-table si besoin.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

