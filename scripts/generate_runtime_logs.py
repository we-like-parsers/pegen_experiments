import pathlib
import subprocess

import git


def main() -> None:
    repo = git.Repo(pathlib.Path.cwd())
    with open("simpy_cpython_timing.log", "w") as file:
        for commit in repo.iter_commits("80f8efb..master"):
            repo.head.reference = commit
            output: str = subprocess.check_output(
                "make simpy_cpython CPYTHON=../cpython/Lib", shell=True
            ).decode("utf-8")
            file.write(f"Commit: {commit.hexsha}\n")
            file.write(f"{output.splitlines()[-2]}\n")
            file.write("\n")
    repo.head.reference = repo.heads.master


if __name__ == "__main__":
    main()
