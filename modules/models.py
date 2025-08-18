from dataclasses import dataclass
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


@dataclass
class Entry:
    course_name: str
    course_id: str
    room: str
    date: datetime
    start_period: int
    end_period: int
    group: str
    sub_group: str = ""

    def is_practice_class(self) -> bool:
        return bool(self.sub_group)
