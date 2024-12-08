import re
import setuptools
import subprocess
import datetime
import os

project_name = "gui4us"
dev_branch_pattern = r"^v\d+\.\d+\.\d+-dev$"
release_tag_pattern = r"^v\d+\.\d+\.\d+$"
today = datetime.datetime.now().strftime("%Y%m%d")


def run_cmd(cmd: str, return_code=False, shell=False):
    cmd = cmd.strip().split(" ")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        shell=shell,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        if return_code:
            return stdout, stderr, result.returncode
        else:
            raise RuntimeError(
                f"The process {cmd} exited with code {result.returncode}, "
                f"stdout: '{stdout}', stderr: {stderr}")
    else:
        if return_code:
            return stdout, stderr, result.returncode
        else:
            return stdout


def get_version_for_branch(branch_name):
    # major.minor
    base_version = ".".join(branch_name.split(".")[:2])
    # Try to find the latest version tag
    tag_on_branch, _, ret = run_cmd(
        cmd=f"git describe --tags --match {base_version}.* --abbrev=0",
        return_code=True
    )
    if ret == 0 and tag_on_branch:
        # This is the release branch with some already available
        # stable versions -- return .dev for the next patch release.
        # Check if this is release tag -- if so, increment the patch
        # and set dev suffix.
        # If it is not a release tag -- return exactly the tag_name
        # with the date suffix.
        if re.match(release_tag_pattern, tag_on_branch):
            major, minor, patch = tag_on_branch.split(".")
            return f"{major}.{minor}.{int(patch)+1}.dev{today}"
        else:
            # Ignore any non-conformat tags.
            return f"{base_version}.0.dev{today}"
    else:
        # There is no relaese tag on this brach -- return major.minor.0.dev tag
        return f"{base_version}.0.dev{today}"


def get_git_version():
    current_branch = run_cmd(cmd="git rev-parse --abbrev-ref HEAD")
    current_tag = run_cmd(cmd="git tag --points-at HEAD")

    def post_process_version(v):
        # Remove 'v' prefix
        return v[1:]

    if len(current_tag.strip()) > 0:
        # If the current commit is tagged as version release -- use that
        # version number.
        # THIS IS STABLE VERSION
        return post_process_version(current_tag)

    # Otherwise -- we have a DEV VERSION
    if re.match(dev_branch_pattern, current_branch):
        return post_process_version(get_version_for_branch(current_branch))
    else:
        # This is probably a feature branch
        # To handle that properly, we will try to find the latest vx.y.z-dev
        # branch, that is also a parent for the current branch.
        commits = run_cmd(cmd="git log --reverse --abbrev-commit --format=%P")
        latest_common_commit = commits.split("\n")[0]
        branches = run_cmd(cmd=f"git branch --contains {latest_common_commit}")
        branches = branches.split("\n")
        # filter out non-release branches
        branches = [b.strip() for b in branches if re.match(dev_branch_pattern, b.strip())]
        if len(branches) == 0:
            raise ValueError("No parent dev branch")
        # sort
        branches = sorted(branches)
        # get the latest one
        branch = branches[-1]
        version = get_version_for_branch(branch)
        current_branch = current_branch.strip().lower().replace("-", ".")
        version = f"{version}+{current_branch}"
        return post_process_version(version)


def write_version_file(version):
    version_file = os.path.join(project_name, "version.py")
    with open(version_file, "w") as f:
        f.write(f'__version__ = "{version}"\n')



if __name__ == "__main__":
    git_version = get_git_version()
    write_version_file(git_version)

    version_namespace = {}
    with open("gui4us/version.py") as f:
        exec(f.read(), version_namespace)

    setuptools.setup(
        name="gui4us",
        version=version_namespace["__version__"],
        author="us4us Ltd.",
        author_email="support@us4us.eu",
        description="GUI 4 ultrasound",
        long_description="GUI 4 ultrasound",
        long_description_content_type="text/markdown",
        url="https://us4us.eu",
        packages=setuptools.find_packages(exclude=[]),
        classifiers=[
            "Development Status :: 1 - Planning",

            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",

            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Embedded Systems",
            "Topic :: Scientific/Engineering :: Bio-Informatics",
            "Topic :: Scientific/Engineering :: Medical Science Apps."
        ],
        entry_points={
            "console_scripts": [
                "gui4us = gui4us:main"
            ]
        },
        install_requires=[
            "arrus>=0.10.0",
            "pyyaml==6.0",
            "PyQt5==5.15.9",
            "PyQt5-Qt5==5.15.2",
            "PyQt5-sip==12.12.1",
            "matplotlib==3.7.2"
        ],
        python_requires='>=3.8'
    )
