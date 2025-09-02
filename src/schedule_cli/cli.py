import calendar
import gettext
from typing import Any, Callable, ParamSpec, TypeVar

import arrow
import click
from rich.table import Table
from rich.console import Console

from .logger import log
from .modules.models import Schedule, Semester
from .modules.getters import LogInError, SemesterGetter, WeeklyScheduleGetter


# Keyring service name
SERVICE_NAME = "schedule-cli"

# Define generic params and return type
P = ParamSpec("P")
R = TypeVar("R")

# Prepare for translation
t = gettext.translation(
    domain="messages", localedir="locales", fallback=True, languages=["en"]
)
_ = t.gettext

# Prepare rich console
console = Console()

# Initialise getters
semester_getter = SemesterGetter()


# Auth options decorator
def auth_options(f: Callable[P, R]) -> Callable[P, R]:
    f = click.option(
        "--password",
        help=_("Your Student Portal's password."),
        prompt=_("Emter your password"),
        hide_input=True,
    )(f)
    f = click.option(
        "--student-id",
        help=_("Your Student Portal's ID."),
        prompt=_("Enter your student ID"),
    )(f)
    return f


# Custom click.ParamType for arrow dates
class ArrowParamType(click.ParamType):
    name = "date"

    def __init__(self, formats: str | list[str] = "YYYY-MM-DD") -> None:
        if isinstance(formats, str):
            self.formats = [formats]
        else:
            self.formats = formats

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> arrow.Arrow:
        if isinstance(value, arrow.Arrow):
            return value

        for fmt in self.formats:
            try:
                return arrow.get(value, fmt)
            except Exception:
                continue

        self.fail(
            f"Invalid date: {value!r} (expected {', '.join(self.formats)})", param, ctx
        )


# Common schedule options decorator
def schedule_options(f: Callable[P, R]) -> Callable[P, R]:
    f = click.option(
        "--custom-date",
        help=_("Any date in specified week (format: DD/MM/YYYY) - Defaults to today."),
        type=ArrowParamType(formats="DD/MM/YYYY"),
        default=arrow.now(),
    )(f)
    f = click.option(
        "--general/--weekly",
        help=_("Fetch general/weeky schedule - Defaults to weekly."),
    )(f)
    f = click.option(
        "--semester-id", help=_("The semester ID."), type=int, required=True
    )(f)
    return f


# Fetch semester based on ID helper function
def fetch_semester(semester_id: int) -> Semester:
    for s in semester_getter.get():
        if s.id_ == semester_id:
            return s
    raise ValueError(f"Unknown semester ID: {semester_id}")


# Fetch schedule helper function
def fetch_schedule(
    semester_id: int,
    general: bool,
    custom_date: arrow.Arrow,
    student_id: str,
    password: str,
) -> Schedule | None:
    try:
        # Fetch semester info
        semester = fetch_semester(semester_id)

        log.info(
            _("Found semester '%(name)s' - Fetching the schedule...")
            % {"name": str(semester)}
        )

        # Fetch schedule
        getter = WeeklyScheduleGetter(student_id, password)
        # TODO: convert getters.py to use Arrow
        return getter.get(semester, custom_date.datetime)
    except LogInError:
        log.error(_("Incorrect student ID or password"))
    except Exception:
        log.exception(_("Cannot fetch schedule"))


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


@cli.command(help=_("View the table of the schedule."))
@schedule_options
@auth_options
def view(
    semester_id: int,
    general: bool,
    custom_date: arrow.Arrow,
    student_id: str,
    password: str,
) -> None:
    schedule = fetch_schedule(semester_id, general, custom_date, student_id, password)
    if schedule is None:
        return

    log.info(
        _("Found %(count)d classes - Displaying the table:")
        % {"count": len(schedule.entries)}
    )

    table = Table(
        title=_("Your schedule (%(start_date)s - %(end_date)s)")
        % {
            "start_date": schedule.start_date.strftime("%d/%m/%Y"),
            "end_date": schedule.end_date.strftime("%d/%m/%Y"),
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
            e.course_name["en"],
            e.room,
            calendar.day_name[e.weekday],
            str(e.start_period),
            str(e.n_periods),
            e.group,
            e.sub_group or "-",
            "✓" if e.is_absent else "",
        )

    console.print(table)


# TODO: Finish export!
# @cli.command(help=_("Export the schedule as JSON."))
# @schedule_option_semester_id()
# @schedule_option_custom_date()
# @click.option(
#     "--output",
#     "-o",
#     required=True,
#     help=_("The specified file path. Must be non-existing."),
# )
# @credential_option_student_id(required=False)
# @credential_option_password(required=False)
# def export(
#     output: str,
#     semester_id: str,
#     custom_date: str | None,
#     student_id: str | None,
#     password: str | None,
# ) -> None:
#     schedule = find_week_schedule(semester_id, custom_date, student_id, password)
#     if schedule is None:
#         return
#     log.info(
#         _("Schedule has been fetched! Exporting to %(path)s...") % {"path": output}
#     )

#     try:
#         with open(output, "x") as file:
#             file.write(json.dumps(schedule.to_json()))
#             log.info(_("Exported successfully!"))
#     except Exception:
#         log.exception(_("Failed to export."))
