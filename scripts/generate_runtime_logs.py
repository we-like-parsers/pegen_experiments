import argparse
import pathlib
import subprocess

import git


argparser = argparse.ArgumentParser(
    prog="generate_runtime_logs",
    description="Helper program to generate runtime logs of running 'make simpy_cpython'",
)
argparser.add_argument("-c", "--cpython", help="The directory where CPython resides")


def main() -> None:
    args = argparser.parse_args()
    cpython_dir = args.cpython or "../cpython"
    lib_dir = str(pathlib.Path(cpython_dir).joinpath("Lib"))
    print(lib_dir)

    repo = git.Repo(pathlib.Path.cwd())
    with open("simpy_cpython_timing.log", "w") as file:
        for commit in repo.iter_commits("80f8efb..master"):
            repo.head.reference = commit
            repo.head.reset(index=True, working_tree=True)
            file.write(f"Commit: {commit.hexsha}\n")
            try:
                output: str = subprocess.check_output(
                    f"make simpy_cpython CPYTHON={lib_dir}", shell=True
                ).decode("utf-8")
                file.write(f"{output.splitlines()[-2]}\n")
            except subprocess.CalledProcessError as e:
                file.write(f"Exit status: {e.returncode}\n")
            file.write("\n")
    repo.head.reference = repo.heads.master
    repo.head.reset(index=True, working_tree=True)


if __name__ == "__main__":
    main()
