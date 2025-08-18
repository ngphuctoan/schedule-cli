import click
import keyring

from rich.table import Table
from rich.console import Console

from modules import ScheduleGetter, get_semesters

SERVICE_NAME = "schedule-cli"

console = Console()

@click.group()
def cli():
    pass


@cli.command()
def get_all_semesters():
    semester_table = Table()

    semester_table.add_column("ID")
    semester_table.add_column("Name")

    for semester in get_semesters():
        semester_table.add_row(str(semester.id_), semester.name)

    console.print(semester_table)


@cli.command()
@click.option("--student-id", required=True)
@click.option("--password", required=True)
def set_account(student_id: str, password: str):
    keyring.set_password(SERVICE_NAME, "student_id", student_id)
    keyring.set_password(SERVICE_NAME, "password", password)
    console.print("[bold green]SUCCESS[/bold green] Account has been saved!")


@cli.command()
@click.option("--semester-id", required=True)
@click.option("--custom-date")
def export(semester_id: str, custom_date: str):
    student_id = keyring.get_password(SERVICE_NAME, "student_id")
    password = keyring.get_password(SERVICE_NAME, "password")

    if student_id is None or password is None:
        console.print("[bold red]ERROR[/bold red] No account set. Please run `set-account` first!")
        return
    
    for semester in get_semesters():
        if str(semester.id_) != semester_id:
            continue

        getter = ScheduleGetter(student_id, password)
        console.print(getter.get_week_schedule(semester))

        return

    console.print(f"[bold red]ERROR[/bold red] No semester with ID {semester_id} found!")


if __name__ == "__main__":
    cli()
