from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Semester:
    id_: int
    name: str | None
    term: int
    year: int
    start_date: datetime

    def __str__(self) -> str:
        return self.name or f"HK{self.term}/{self.year}-{self.year + 1}"

    def to_json(self) -> dict:
        data = asdict(self)
        data.pop("start_date", None)
        return data


@dataclass
class Entry:
    course_name: str
    course_id: str
    room: str
    weekday: int
    start_period: int
    n_periods: int
    group: str
    sub_group: str = ""
    is_absent: bool = False

    def is_practice_class(self) -> bool:
        return bool(self.sub_group)

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Schedule:
    semester: Semester
    start_date: datetime
    end_date: datetime
    entries: list[Entry]

    def to_json(self) -> dict:
        return {
            "semester": self.semester.to_json(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "entries": [entry.to_json() for entry in self.entries],
        }
