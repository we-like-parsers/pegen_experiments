"""Usage: python -m scripts.test_pypi_packages"""
import os
import glob
import subprocess
import tarfile
import zipfile
import shutil

from typing import Generator, Optional

from scripts import test_parse_directory


def get_packages() -> Generator[str, None, None]:
    all_packages = (
        glob.glob("./data/*.tar.gz") + glob.glob("./data/*.zip") + glob.glob("./data/*.tgz")
    )
    for package in all_packages:
        yield package


def extract_files(filename: str) -> None:
    if tarfile.is_tarfile(filename):
        tarfile.open(filename).extractall("data")
    elif zipfile.is_zipfile(filename):
        zipfile.ZipFile(filename).extractall("data")
    else:
        raise ValueError(f"Could not identify type of compressed file {filename}")


def find_dirname() -> str:
    for name in os.listdir("data"):
        full_path = os.path.join("data", name)
        if os.path.isdir(full_path):
            return full_path
    assert False  # This is to fix mypy, should never be reached


def run_tests(dirname: str) -> None:
    test_parse_directory.main(
        dirname,
        "data/simpy.gram",
        verbose=False,
        excluded_files=[
            "*/failset/*",
            "*/failset/**",
            "*/failset/**/*",
            "*/test2to3/*",
            "*/test2to3/**/*",
            "*/bad*",
            "*/lib2to3/tests/data/*",
        ],
        skip_actions=False,
        tree_arg=False,
        short=True,
    )


def main() -> None:
    for package in get_packages():
        print(f"Extracting files from {package}... ", end="")
        try:
            extract_files(package)
            print("Done")
        except ValueError as e:
            print(e)
            continue

        print(f"Trying to parse all python files ... ", end="")
        dirname = find_dirname()
        try:
            run_tests(dirname)
            print("Done")
        except subprocess.CalledProcessError as e:
            print(f"Failed to parse {dirname}")
            continue
        finally:
            shutil.rmtree(dirname)


if __name__ == "__main__":
    main()
