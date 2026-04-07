from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

# import icecream
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

from fastbpmn.docs.plugin.util import build_file, process_index

if TYPE_CHECKING:
    from fastbpmn import Process, YioMinion
    from fastbpmn.task import TaskProperties


class YioMinionDocs(BasePlugin):
    # pylint: disable=unused-argument

    __slots__ = ["minion", "files"]

    def __init__(self, minion: "YioMinion") -> None:
        self.minion = minion
        self.files: List[File] = []
        self.sections: List[Section] = []
        self.pages: List[Page] = []
        super().__init__()

    def build_process_documentation(
        self, process: "Process", *, config: MkDocsConfig
    ) -> Tuple[Section, List[Page], List[File]]:

        pages = []
        files = []

        title = process.title
        dirname = process.process_definition_key or "generic"

        docs_dir: Path = Path(config["docs_dir"])
        process_dir: Path = docs_dir.joinpath(dirname)

        page, file = process_index(process, process_dir, config=config)
        files.append(file)
        pages.append(page)

        for task_props in process.task_props:
            page, file = build_file(task_props, file_dir=process_dir, config=config)

            files.append(file)
            pages.append(page)

        section = Section(title=title, children=pages)
        for page in pages:
            page.parent = section

        return section, pages, files

    def build_non_process_task_documentation(
        self,
        title: str,
        task_props: List["TaskProperties"],
        *,
        config: MkDocsConfig,
        description: Optional[str] = None,
    ) -> Tuple[Section, List[Page], List[File]]:
        # pylint: disable=unused-argument

        pages = []
        files = []

        dirname = "generic"

        docs_dir: Path = Path(config["docs_dir"])
        process_dir: Path = docs_dir.joinpath(dirname)

        for task_prop in task_props:
            page, file = build_file(task_prop, file_dir=process_dir, config=config)
            pages.append(page)
            files.append(file)

        section = Section(title, pages)

        return section, pages, files

    def build_files(self, *, config: MkDocsConfig) -> None:
        """
        We have to create a file per each ExternalTask
        """
        self.sections = []
        self.pages = []
        self.files = []

        for process in self.minion.processes:
            section, pages, files = self.build_process_documentation(
                process, config=config
            )

            self.sections.append(section)
            self.pages.extend(pages)
            self.files.extend(files)

        if len(self.minion.task_props_without_processes) > 0:
            section, pages, files = self.build_non_process_task_documentation(
                title="Generics",
                task_props=self.minion.task_props_without_processes,
                config=config,
            )

            self.sections.append(section)
            self.pages.extend(pages)
            self.files.extend(files)

    def clean_files(self):
        """
        After build is completed we have to remove the files created per ExternalTask
        """

    def on_pre_build(self, *, config: MkDocsConfig) -> None:
        """
        Use the minion instance to generate all required files to be included within the generated docs
        - markdown file for each process
        - markdown file for each external task
        """
        self.build_files(config=config)

    def clean(self):
        """
        Remove all the contents related with documentation build
        - Remove generated files
        - Remove pictures ...
        """
        self.clean_files()

    def on_post_build(self, *, config: MkDocsConfig) -> None:
        """
        Execute clean method to release allocated resources
        """
        self.clean()

    def on_build_error(self, *, error: Exception) -> None:
        """
        Execute clean method to release allocated resources
        """
        self.clean()

    def on_files(self, files: Files, *, config: MkDocsConfig) -> Optional[Files]:
        # icecream.ic(f"Build docs for {self.minion.name}")

        for file in self.files:
            files.append(file)

        return files

    def static_file(self, name: str, files: Files, *, config: MkDocsConfig) -> Page:

        imprint_file = next(file for file in files if file.name == name)

        return Page(title=None, file=imprint_file, config=config)

    def imprint(self, files: Files, *, config: MkDocsConfig) -> Page:
        return self.static_file("impressum", files, config=config)

    def contact(self, files: Files, *, config: MkDocsConfig) -> Page:
        return self.static_file("kontakt", files, config=config)

    def on_nav(
        self, nav: Navigation, *, config: MkDocsConfig, files: Files
    ) -> Optional[Navigation]:

        nav.pages.extend(self.pages)
        nav.items.extend(self.sections)

        contact = self.contact(files, config=config)
        imprint = self.imprint(files, config=config)

        nav.pages.append(contact)
        nav.items.append(contact)
        nav.pages.append(imprint)
        nav.items.append(imprint)

        return nav
