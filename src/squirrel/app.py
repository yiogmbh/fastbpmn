import typer

from .flavours.camunda7.entrypoint import camunda7_app

app = typer.Typer()

app.add_typer(camunda7_app, help="Start squirrel using camunda7 flavour.")
