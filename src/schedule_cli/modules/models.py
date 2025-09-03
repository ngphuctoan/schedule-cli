from typing import TypedDict
from dataclasses import asdict, dataclass

import arrow


@dataclass
class Semester:
    """
    Academic semester.

    Attributes:
        id_ (int): Unique identifier from the API.
        name (str, optional): Name of the semester.
        term (int): Term number (e.g., 1 for first term).
        year (int): Academic year.
        _start_date (arrow.Arrow): Start date of the semester.
    """

    id_: int
    name: str | None
    term: int
    year: int
    _start_date: arrow.Arrow

    def __str__(self) -> str:
        """
        Return the semester name, or 'HK{term}/{year}-{year+1}' if None.

        Returns:
            str: Human-readable name of the semester.
        """
        return self.name or f"HK{self.term}/{self.year}-{self.year + 1}"

    def to_json(self) -> dict:
        """
        Return a JSON-serialisable dict. Excludes `_start_date` field.

        Returns:
            dict: Dictionary representation of the semester.
        """
        data = asdict(self)
        data.pop("_start_date", None)
        return data


class CourseName(TypedDict):
    """
    Name of the course.

    Attributes:
        en (str): English name.
        vi (str): Vietnamese name.
    """

    en: str
    vi: str


@dataclass
class Entry:
    """
    Entry/class in a schedule.

    Attributes:
        course_name (CourseName): Name of the course.
        course_id (str): ID of the course.
        room (str): Room label.
        weelday (int): Day of the week.
        start_period (int): Start period.
        n_periods (int): Number of periods.
        group (str): Group code.
        sub_group (str): Sub-group code. Empty for theory classes.
        is_absent (bool): Whether the entry absent.
    """

    course_name: CourseName
    course_id: str
    room: str
    weekday: int
    start_period: int
    n_periods: int
    group: str
    sub_group: str = ""
    is_absent: bool = False

    def is_practice_class(self) -> bool:
        """
        Return True of `sub_group` is not empty.

        Returns:
            bool: Wheter this entry is a practice class.
        """
        return bool(self.sub_group)

    def to_json(self) -> dict:
        """
        Return a JSON-serialisable dict.

        Returns:
            dict: Dictionary representation of the entry.
        """
        return asdict(self)


@dataclass
class Schedule:
    """
    Schedule.

    Attributes:
        semester (Semester): Semester of the schedule.
        start_date (arrow.Arrow): Start date of the week.
        end_date (arrow.Arrow): End date of the week.
        entries (list[Entry]): Schedule entries/classes.
    """

    semester: Semester
    start_date: arrow.Arrow
    end_date: arrow.Arrow
    entries: list[Entry]

    def to_json(self) -> dict:
        """
        Return a JSON-serialisable dict. `arrow.Arrow` dates converted to ISO strings.

        Returns:
            dict: Dictionary representation of the schedule.
        """
        return {
            "semester": self.semester.to_json(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "entries": [entry.to_json() for entry in self.entries],
        }
