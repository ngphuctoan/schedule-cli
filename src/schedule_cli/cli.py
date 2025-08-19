from datetime import datetime
import click
import keyring
from rich.table import Table
from rich.console import Console

from schedule_cli.logger import log
from schedule_cli.modules.getter import ScheduleGetter, get_semesters
from schedule_cli.modules.models import Entry, Semester
from schedule_cli.modules.constants import DATE_FORMAT

SERVICE_NAME = "schedule-cli"
console = Console()


def get_credentials() -> tuple[str, str] | tuple[None, None]:
    student_id = keyring.get_password(SERVICE_NAME, "student_id")
    password = keyring.get_password(SERVICE_NAME, "password")

    if student_id is None or password is None:
        log.error("No account set! Please run this command first:\n$ schedule-cli set-account --student-id STUDENT_ID --password PASSWORD")
        return None, None

    return student_id, password


def find_semester(semester_id: str) -> Semester | None:
    for semester in get_semesters():
        if str(semester.id_) == semester_id:
            return semester
    return None


def find_week_schedule(semester_id: str, custom_date: str | None) -> list[Entry | None] | None:
    student_id, password = get_credentials()
    if student_id is None:
        return None

    semester = find_semester(semester_id)
    if semester is None:
        log.error(f"No semester found with ID {semester_id}! For available semesters please run:\n$ schedule-cli fetch-semesters")
        return None

    log.info(f"Found semester '{semester.name}', fetching the schedule...")
    getter = ScheduleGetter(student_id, password)

    if custom_date is not None:
        formatted_date = datetime.strptime(custom_date, DATE_FORMAT)
    else:
        formatted_date = None
    return getter.get_week_schedule(semester, formatted_date)


@click.group()
def cli():
    pass


@cli.command(help="Fetch the available semester(s).")
def fetch_semesters():
    semesters = get_semesters()
    log.info(f"Found {len(semesters)} semester(s), showing list:")

    table = Table(title="Available semester(s)")
    table.add_column("ID", justify="right")
    table.add_column("Name")

    for s in semesters:
        table.add_row(str(s.id_), s.name)

    console.print(table)


@cli.command(help="Save log in credentials to the keyring.")
@click.option(
    "--student-id",
    "-i",
    required=True,
    help="Your student ID used on the Student Portal.",
)
@click.option("--password", "-p", required=True, help="Your password used on the Student Portal.")
def set_account(student_id: str, password: str):
    keyring.set_password(SERVICE_NAME, "student_id", student_id)
    keyring.set_password(SERVICE_NAME, "password", password)
    log.info("Account has been saved!")


@cli.command(help="View the schedule as a table.")
@click.option("--semester-id", "-s", required=True, help="The ID of the semester.")
@click.option(
    "--custom-date",
    "-d",
    help="Any date within the specified (format: DD/MM/YYYY). Defaults to today.",
)
def view(semester_id: str, custom_date: str | None):
    schedule = find_week_schedule(semester_id, custom_date)
    if schedule is None:
        return
    log.info(f"Found {len(schedule)} entry(s), showing list:")

    table = Table(title="Available entry(s)")
    table.add_column("ID")
    table.add_column("Course")
    table.add_column("Room")
    table.add_column("Date")
    table.add_column("Start period", justify="right")
    table.add_column("End period", justify="right")
    table.add_column("Group", justify="right")
    table.add_column("Sub group", justify="right")
    table.add_column("Is absent", justify="center", style="red")

    for e in schedule:
        table.add_row(
            e.course_id,
            e.course_name,
            e.room,
            datetime.strftime(e.date, DATE_FORMAT),
            str(e.start_period),
            str(e.end_period),
            e.group,
            e.sub_group,
            "✓" if e.is_absent else "",
        )

    console.print(table)


@cli.command(help="Export the schedule to a JSON file")
@click.option(
    "--output",
    "-o",
    required=True,
    help="Path to save the schedule. Must be a non-existing file.",
)
@click.option("--semester-id", "-s", required=True, help="The ID of the semester.")
@click.option(
    "--custom-date",
    "-d",
    help="Any date within the specified (format: DD/MM/YYYY). Defaults to today.",
)
def export(output: str, semester_id: str, custom_date: str | None):
    schedule = find_week_schedule(semester_id, custom_date)
    if schedule is None:
        return
    log.info(f"Fetched schedule! Exporting to '{output}'...")

    with open(output, "x") as file:
        file.write(f"[{','.join([e.to_json() for e in schedule])}]")
        log.info("Schedule has been exported!")


if __name__ == "__main__":
    cli()
