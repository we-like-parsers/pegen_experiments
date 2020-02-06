import os
import json
import shutil

from typing import Dict, Any
from urllib.request import urlretrieve

# This can be either the number of packages to download or 'ALL' to download
# all 4000 provided by https://hugovk.github.io/top-pypi-packages/
NUMBER_OF_PACKAGES = 3


def load_json(filename: str) -> Dict[Any, Any]:
    with open(os.path.join("data", f"{filename}.json"), "r") as f:
        j = json.loads(f.read())
    return j


def remove_json(filename: str) -> None:
    path = os.path.join("data", f"{filename}.json")
    os.remove(path)


def download_package_json(package_name: str) -> None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    urlretrieve(url, os.path.join("data", f"{package_name}.json"))


def download_package_code(name: str, package_json: Dict[Any, Any]) -> None:
    source_index = -1
    for idx, url_info in enumerate(package_json["urls"]):
        if url_info["python_version"] == "source":
            source_index = idx
            break
    filename = package_json["urls"][source_index]["filename"]
    url = package_json["urls"][source_index]["url"]
    urlretrieve(url, os.path.join("data", filename))


def main() -> None:
    top_pypi_packages = load_json("top-pypi-packages-365-days")
    if isinstance(NUMBER_OF_PACKAGES, int):
        top_pypi_packages = top_pypi_packages["rows"][:NUMBER_OF_PACKAGES]
    elif isinstance(NUMBER_OF_PACKAGES, str) and NUMBER_OF_PACKAGES == "ALL":
        top_pypi_packages = top_pypi_packages["rows"]
    else:
        raise AssertionError("Unknown value for NUMBER_OF_PACKAGES")

    for package in top_pypi_packages:
        package_name = package["project"]

        print(f"Downloading JSON Data for {package_name}... ", end="")
        download_package_json(package_name)
        print("Done")

        package_json = load_json(package_name)
        try:
            print(f"Dowloading and compressing package {package_name} ... ", end="")
            download_package_code(package_name, package_json)
            print("Done")
        except (IndexError, KeyError):
            print(f"Could not locate source for {package_name}")
            continue
        finally:
            remove_json(package_name)


if __name__ == "__main__":
    main()
