import os
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory


def mkdocs_sitedir(site_dir: Path) -> Path:
    """
    Check for site_dir being a valid location to
    write the generated documentation.
    """
    site_dir = site_dir.absolute()

    # Check existence
    if not site_dir.exists():
        site_dir.mkdir(parents=True, exist_ok=False)
        return site_dir

    if site_dir.exists() and not site_dir.is_dir():
        raise ValueError("Specify a non existent or empty directory as site_dir")

    return site_dir


@contextmanager
def mkdocs_directory():
    traversable = resources.files("fastbpmn.data")
    mkdocs_resources = None
    if traversable.is_dir():
        for content in traversable.iterdir():
            if content.is_dir() and content.name == "mkdocs":
                mkdocs_resources = content

    if mkdocs_resources is None:
        raise FileNotFoundError(
            "Unable to locate package resources, this should not happen"
        )

    with (
        TemporaryDirectory(prefix="yio-minions-doc_") as build_dir,
        resources.as_file(mkdocs_resources) as tmp_dir,
    ):
        original_working_directory = os.getcwd()

        copytree(tmp_dir, build_dir, dirs_exist_ok=True)
        try:
            os.chdir(build_dir)
            yield build_dir
        finally:
            os.chdir(original_working_directory)
