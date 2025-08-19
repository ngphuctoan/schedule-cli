import json
import locale
import gettext
import calendar
from datetime import datetime

import click
import keyring
from rich.table import Table
from rich.console import Console

from schedule_cli.logger import log
from schedule_cli.modules.getters import (
    SemesterGetter,
    WeeklyScheduleGetter,
    LogInError,
)
from schedule_cli.modules.models import Schedule, Semester
from schedule_cli.modules.constants import DATE_FORMAT

SERVICE_NAME = "schedule-cli"

# Uncomment to test app in Vietnamese.
locale.setlocale(locale.LC_ALL, "vi_VN")

console = Console()
semester_getter = SemesterGetter()

lang = locale.getlocale()[0]
if lang is None:
    lang = locale.getdefaultlocale()[0]

t = gettext.translation(
    domain="messages", localedir="locales", languages=[lang], fallback=True
)
_ = t.gettext


def credential_option_student_id(required: bool = True):
    return click.option(
        "--student-id", "-i", required=required, help=_("Your student ID.")
    )


def credential_option_password(required: bool = True):
    return click.option("--password", "-p", required=required, help=_("Your password."))


def schedule_option_semester_id():
    return click.option(
        "--semester-id", "-s", required=True, help=_("The semester ID.")
    )


def schedule_option_custom_date():
    return click.option(
        "--custom-date",
        "-d",
        help=_(
            "Any date within the specified week (format: DD/MM/YYYY) - Defaults to today."
        ),
    )


def get_credentials_from_keychain() -> tuple[str, str] | tuple[None, None]:
    student_id = keyring.get_password(SERVICE_NAME, "student_id")
    password = keyring.get_password(SERVICE_NAME, "password")

    if student_id is None or password is None:
        log.error(
            _("No account is set - Please run `%(command)s` first!")
            % {"command": "set-account"}
        )
        return None, None

    return student_id, password


def find_semester(semester_id: str) -> Semester | None:
    for semester in semester_getter.get():
        if str(semester.id_) == semester_id:
            return semester
    return None


def find_week_schedule(
    semester_id: str,
    custom_date: str | None,
    student_id: str | None,
    password: str | None,
) -> Schedule | None:
    if student_id is None or password is None:
        student_id, password = get_credentials_from_keychain()
    else:
        log.info(_("Using the provided account instead of local storage."))

    if student_id is None or password is None:
        return None

    semester = find_semester(semester_id)
    if semester is None:
        log.error(
            _("Unknown semester ID: %(id)s - Use `%(command)s` to list all semesters.")
            % {"id": semester_id, "command": "fetch-semesters"}
        )
        return None

    log.info(
        _("Found semester '%(name)s' - Fetching the schedule...")
        % {"name": str(semester)}
    )
    getter = WeeklyScheduleGetter(student_id, password)

    if custom_date is not None:
        formatted_date = datetime.strptime(custom_date, DATE_FORMAT)
    else:
        formatted_date = None

    try:
        return getter.get(semester, formatted_date)
    except LogInError:
        log.error(_("Invalid student ID or password!"))
    except Exception:
        log.exception(_("Something went wrong."))


@click.group()
def cli() -> None:
    pass


@cli.command(help=_("Fetch all semesters."))
def fetch_semesters() -> None:
    semesters = semester_getter.get()

    log.info(
        _("Found %(count)d semesters - Displaying the table:")
        % {"count": len(semesters)}
    )

    table = Table(title=_("All semesters"))
    table.add_column(_("ID"), justify="right")
    table.add_column(_("Name"))

    for s in semesters:
        table.add_row(str(s.id_), s.name)

    console.print(table)


@cli.command(help=_("Save your Student Portal account locally."))
@credential_option_student_id()
@credential_option_password()
def set_account(student_id: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, "student_id", student_id)
    keyring.set_password(SERVICE_NAME, "password", password)
    log.info(_("Your account has been saved!"))


@cli.command(help=_("View the table of the schedule."))
@schedule_option_semester_id()
@schedule_option_custom_date()
@credential_option_student_id(required=False)
@credential_option_password(required=False)
def view(
    semester_id: str,
    custom_date: str | None,
    student_id: str | None,
    password: str | None,
) -> None:
    schedule = find_week_schedule(semester_id, custom_date, student_id, password)
    if schedule is None:
        return

    log.info(
        t.ngettext(
            "Found 1 entry - Displaying the table:",
            "Found %(count)d entries - Displaying the table:",
            n=len(schedule.entries),
        )
        % {"count": len(schedule.entries)}
    )

    table = Table(
        title=_("Your schedule (%(start_date)s - %(end_date)s)")
        % {
            "start_date": schedule.start_date.strftime(DATE_FORMAT),
            "end_date": schedule.end_date.strftime(DATE_FORMAT),
        }
    )
    table.add_column(_("ID"))
    table.add_column(_("Course"))
    table.add_column(_("Room"))
    table.add_column(_("Weekday"))
    table.add_column(_("Period"), justify="right")
    table.add_column(_("Duration"), justify="right")
    table.add_column(_("Group"), justify="right")
    table.add_column(_("Sub group"), justify="right")
    table.add_column(_("Is absent"), justify="center", style="red")

    for e in schedule.entries:
        table.add_row(
            e.course_id,
            e.course_name,
            e.room,
            calendar.day_name[e.weekday],
            str(e.start_period),
            str(e.n_periods),
            e.group,
            e.sub_group or "-",
            "✓" if e.is_absent else "",
        )

    console.print(table)


@cli.command(help=_("Export the schedule as JSON."))
@schedule_option_semester_id()
@schedule_option_custom_date()
@click.option(
    "--output",
    "-o",
    required=True,
    help=_("The specified file path. Must be non-existing."),
)
@credential_option_student_id(required=False)
@credential_option_password(required=False)
def export(
    output: str,
    semester_id: str,
    custom_date: str | None,
    student_id: str | None,
    password: str | None,
) -> None:
    schedule = find_week_schedule(semester_id, custom_date, student_id, password)
    if schedule is None:
        return
    log.info(
        _("Schedule has been fetched! Exporting to %(path)s...") % {"path": output}
    )

    with open(output, "x") as file:
        try:
            file.write(json.dumps(schedule.to_json()))
            log.info(_("Exported successfully!"))
        except Exception:
            log.exception(_("Failed to export."))


if __name__ == "__main__":
    cli()
