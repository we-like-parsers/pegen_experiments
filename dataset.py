#! /usr/bin/env python3

# TODO: Print errors to stderr?

import argparse
import ast
import json
from pegen.testutil import try_our_parser
import sqlite3
import sys
import time
from typing import *


schema_str = """
uid text UNIQUE,
content text,
length integer,
line_count integer,
syntax_err_line_no integer,
syntax_err_offset integer,
error_type text,
error_message text,
tags text
"""
schema_items = [x.strip() for x in schema_str.split(",")]
schema_pairs = [x.split(None, 1) for x in schema_items]

more_schema_str = """
ast_syntax_err_line_no integer,
ast_syntax_err_offset integer,
ast_error_type text,
ast_error_message text,
pegen_syntax_err_line_no integer,
pegen_syntax_err_offset integer,
pegen_error_type text,
pegen_error_message text
"""
more_schema_items = [x.strip() for x in more_schema_str.split(",")]
more_schema_pairs = [x.split(None, 1) for x in more_schema_items]

all_schema_items = schema_items + more_schema_items
all_schema_pairs = schema_pairs + more_schema_pairs


class DatasetDB:
    """Wrap a sqlite3 database containing the dataset."""

    def __init__(self) -> None:
        self.open_db()
        self.create_tables()

    def open_db(self) -> None:
        self.dbname = "dset.db"
        self.db = sqlite3.connect(self.dbname)

    def commit(self) -> None:
        self.db.commit()

    def execute(self, sql: str, values: Iterable[object] = ()) -> Iterable[Any]:
        c = self.db.cursor()
        c.row_factory = sqlite3.Row
        try:
            return c.execute(sql, values)
        except sqlite3.Error as err:
            print(f"sql = {sql!r}")
            print(f"values = {values!r}")
            raise

    def create_tables(self) -> None:
        self.execute(f"CREATE TABLE IF NOT EXISTS dataset ({schema_str},{more_schema_str})")

    def insert_record(self, record: Dict[str, object]) -> None:
        values = [record[key] for key, _ in schema_pairs]
        col_names = ",".join(key for key, _ in schema_pairs)
        qmarks = ",".join("?" for _ in range(len(values)))
        self.execute(f"INSERT INTO dataset ({col_names}) VALUES ({qmarks})", values)

    def get_record(self, uid: str) -> Optional[sqlite3.Row]:
        records = list(self.execute(f"SELECT * FROM dataset WHERE uid = ?", [uid]))
        if not records:
            print(f"Nothing at uid {uid}")
            return None
        return records[0]

    def update_record(self, uid: str, values: Dict[str, object]) -> None:
        set_stuff = ", ".join([f"{key} = ?" for key in values])
        values_stuff = list(values.values())
        values_stuff.append(uid)
        self.execute(f"UPDATE dataset SET {set_stuff} WHERE uid = (?)", values_stuff)


def print_record(record: Optional[sqlite3.Row], uid: Optional[str] = None, verbose: bool = False) -> None:
    print("-" * 72)
    if record is None:
        if uid:
            print(f"Nothing at {uid}")
        else:
            print(f"Nothing")
    else:
        keys: List[str] = record.keys()  # type: ignore [no-untyped-call]
        for name, field in zip(keys, record):
            if field is not None:
                if verbose:
                    if isinstance(field, str) and "\n" in field:
                        print(f"{name} --> '''\\")
                        print(field)
                        print("'''")
                    else:
                        print(f"{name} --> {field!r}")
                else:
                    print(f"{name} --> {field!r:.100}")


def clear_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    count = list(db.execute("SELECT COUNT(*) FROM dataset"))[0][0]
    db.execute("DELETE FROM dataset")
    db.commit()
    print(f"Deleted {count} records from {db.dbname}")


def load_main(args: argparse.Namespace) -> None:
    with open(args.file) as f:
        dataset = json.load(f)
    db = DatasetDB()
    count = 0
    for uid, record in dataset.items():
        record["uid"] = uid
        record["tags"] = ",".join(record["tags"])
        db.insert_record(record)
        count += 1
    db.commit()
    print(f"Inserted {count} records into {db.dbname} from {args.file}")


def reload_main(args: argparse.Namespace) -> None:
    # TODO: Refactor to reuse db
    clear_main(args)
    load_main(args)


def validate_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    records = db.execute(
        f"SELECT * FROM dataset ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
    )
    count = 0
    for record in records:
        uid = record["uid"]
        try:
            ast.parse(record["content"])
        except SyntaxError as err:
            db.update_record(
                uid,
                dict(
                    ast_error_type=err.__class__.__name__,
                    ast_error_message=err.msg,
                    ast_syntax_err_line_no=err.lineno,
                    ast_syntax_err_offset=err.offset,
                ),
            )
        else:
            db.update_record(
                uid,
                dict(
                    ast_error_type="",
                    ast_error_message="",
                    ast_syntax_err_line_no=0,
                    ast_syntax_err_offset=0,
                ),
            )
        if args.print:
            print_record(db.get_record(uid))
        count += 1
    db.commit()  # TODO: If it's a large number, commit batches?
    if not count:
        print(f"Nothing to validate at offset {args.start}")
    else:
        print()
        print(f"Validated {count} records")


def pegen_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    records = db.execute(
        f"SELECT * FROM dataset ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
    )
    skipped = 0
    parsed = 0
    for record in records:
        uid = record["uid"]
        print(f"\r{skipped:10d} skipped; {parsed:10d} parsed; next: {uid:<10s}", end="", flush=True, file=sys.stderr)
        if args.lazy and record["pegen_error_type"] is not None:
            if args.print:
                print(file=sys.stderr)
                print(f"Skipping uid {uid}, already parsed")
            skipped += 1
            continue
        t0 = time.time()
        err, parser = try_our_parser(record["content"])
        dt = time.time() - t0
        if dt > 0.1:
            print(f"took {dt:.3f} seconds", file=sys.stderr)  # Show uid of slow records
        if err is None:
            db.update_record(
                uid,
                dict(
                    pegen_error_type="",
                    pegen_error_message="",
                    pegen_syntax_err_line_no=0,
                    pegen_syntax_err_offset=0,
                ),
            )
        elif isinstance(err, SyntaxError):
            db.update_record(
                uid,
                dict(
                    pegen_error_type=err.__class__.__name__,
                    pegen_error_message=err.msg,
                    pegen_syntax_err_line_no=err.lineno,
                    pegen_syntax_err_offset=err.offset,
                ),
            )
        else:
            db.update_record(
                uid,
                dict(
                    pegen_error_type=err.__class__.__name__,
                    pegen_error_message=err.args[0],
                    pegen_syntax_err_line_no=0,
                    pegen_syntax_err_offset=0,
                ),
            )
        if args.print:
            print(file=sys.stderr)
            print_record(db.get_record(uid))
        parsed += 1
        if parsed % 100 == 0:
            print("committing", file=sys.stderr)
            db.commit()
    print(f"\r{skipped:10d} skipped; {parsed:10d} parsed" + " "*20, file=sys.stderr)
    db.commit()  # TODO: If it's a large number, commit batches?


def print_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    if args.uid:
        sql = "SELECT * FROM dataset WHERE uid = ?"
        values = [args.uid]
    else:
        sql = f"SELECT * FROM dataset ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
        values = []
    records = db.execute(sql, values)
    count = 0
    for record in records:
        uid = record["uid"]
        print_record(record, uid, verbose=args.verbose or bool(args.uid))
        count += 1
    if not count:
        print(f"Nothing to print at offset {args.start}")
    else:
        print()
        print(f"Printed {count} records")


def query_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    records = db.execute(
        f"SELECT {args.what} FROM dataset WHERE {args.query} ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
    )
    count = 0
    for record in records:
        print_record(record)
        count += 1
    if not count:
        print(f"No query results at offset {args.start}")
    else:
        print()
        print(f"Printed {count} query results")


argv_parser = argparse.ArgumentParser()
sub = argv_parser.add_subparsers(dest="sub̊command", required=True)

clear_parser = sub.add_parser("clear")
clear_parser.set_defaults(func=clear_main)

load_parser = sub.add_parser("load")
load_parser.add_argument("-f", "--file", default="data/parse_errors.json")
load_parser.set_defaults(func=load_main)

reload_parser = sub.add_parser("reload")
reload_parser.add_argument("-f", "--file", default="data/parse_errors.json")
reload_parser.set_defaults(func=reload_main)

validate_parser = sub.add_parser("validate", aliases=["v"])
validate_parser.add_argument("-s", "--start", type=int, default=0)
validate_parser.add_argument("-n", "--number", type=int, default=1)
validate_parser.add_argument("-p", "--print", action="store_true")
validate_parser.set_defaults(func=validate_main)

pegen_parser = sub.add_parser("pegen", aliases=["peg", "g"])
pegen_parser.add_argument("-s", "--start", type=int, default=0)
pegen_parser.add_argument("-n", "--number", type=int, default=1)
pegen_parser.add_argument("-p", "--print", action="store_true")
pegen_parser.add_argument("-l", "--lazy", action="store_true")
pegen_parser.set_defaults(func=pegen_main)

print_parser = sub.add_parser("print", aliases=["p"])
print_parser.add_argument("-s", "--start", type=int, default=0)
print_parser.add_argument("-n", "--number", type=int, default=1)
print_parser.add_argument("-u", "--uid")
print_parser.add_argument("-v", "--verbose", action="store_true")
print_parser.set_defaults(func=print_main)

query_parser = sub.add_parser("query", aliases=["q"])
query_parser.add_argument("-s", "--start", type=int, default=0)
query_parser.add_argument("-n", "--number", type=int, default=1)
query_parser.add_argument("-w", "--what", default="*")
query_parser.add_argument("query", nargs="?", default="TRUE")
query_parser.set_defaults(func=query_main)


def main() -> None:
    args = argv_parser.parse_args()
    if args.number == 0:
        args.number = 999999999
    args.func(args)


if __name__ == "__main__":
    main()
