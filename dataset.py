#! /usr/bin/env python3

# TODO: Print errors to stderr?

import argparse
import ast
import json
import sqlite3
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
ast_error_message text
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


def print_record(record: Optional[sqlite3.Row], uid: Optional[str] = None) -> None:
    print("-" * 72)
    if record is None:
        if uid:
            print(f"Nothing at {uid}")
        else:
            print(f"Nothing")
    else:
        for name, field in zip(record.keys(), record):  # type: ignore [no-untyped-call]
            if field is not None:
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
    uids = db.execute(
        f"SELECT uid FROM dataset ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
    )
    count = 0
    for [uid] in uids:  # TODO: just get all the records
        record = db.get_record(uid)
        if record is None:
            print(f"No record for {uid}")
            continue
        try:
            ast.parse(record["content"])
        except SyntaxError as err:
            ast_error_type = err.__class__.__name__
            ast_error_message = err.msg
            ast_syntax_err_line_no = err.lineno
            ast_syntax_err_offset = err.offset
            db.update_record(
                uid,
                dict(
                    ast_error_type=ast_error_type,
                    ast_error_message=ast_error_message,
                    ast_syntax_err_line_no=ast_syntax_err_line_no,
                    ast_syntax_err_offset=ast_syntax_err_offset,
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


def print_main(args: argparse.Namespace) -> None:
    db = DatasetDB()
    uids = db.execute(
        f"SELECT uid FROM dataset ORDER BY uid ASC LIMIT {args.number} OFFSET {args.start}"
    )
    count = 0
    for [uid] in uids:
        record = db.get_record(uid)
        print_record(record, uid)
        count += 1
    if not count:
        print(f"Nothing to print at offset {args.start}")
    else:
        print()
        print(f"Printed {count} records")


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

print_parser = sub.add_parser("print", aliases=["p"])
print_parser.add_argument("-s", "--start", type=int, default=0)
print_parser.add_argument("-n", "--number", type=int, default=1)
print_parser.set_defaults(func=print_main)


def main() -> None:
    args = argv_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
