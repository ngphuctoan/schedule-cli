import re
from typing import Any, TypeAlias
from dataclasses import dataclass
from abc import ABC, abstractmethod

import arrow
import requests
from requests import Response
from bs4.element import Tag
from bs4 import BeautifulSoup as Soup

from .constants import DATE_FORMAT
from .models import Entry, Schedule, Semester

GetterResult: TypeAlias = tuple[Response, Soup]


class LogInError(Exception):
    """Raised when logging in fails."""


@dataclass
class Auth:
    """
    Student Portal account.

    Attributes:
        student_id (str): Student ID.
        password (str): Password.
    """

    student_id: str
    password: str

    def to_form_data(self) -> dict[str, str]:
        """Return form fields for API requests."""
        return {"user": self.student_id, "pass": self.password}


@dataclass
class PostBackForm:
    """
    Request body for ASP.NET postbacks.

    Attributes:
        viewstate (str): Value of `__VIEWSTATE`.
        viewstategenerator (str): Value of `__VIEWSTATEGENERATOR`.
    """

    viewstate: str = ""
    viewstategenerator: str = ""

    def to_form_data(self) -> dict[str, Any]:
        """Return form fields for API requests."""
        return {
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstategenerator,
        }


class BaseGetter(ABC):
    """Abstract base class for all getter implementations."""

    @abstractmethod
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Retrive data. Must be implemented by subclasses."""


class SemesterGetter(BaseGetter):
    """Getter for academic semesters from the API."""

    API_URL = "https://thoikhoabieudukien.tdtu.edu.vn/API/XemKetQuaDangKy/LoadHocKy"

    def get(self) -> list[Semester]:
        """
        Retrieve a list of semesters sorted by ID.

        Returns:
            list[Semester]: List of semesters available from the API.
        """
        semesters: list[Semester] = []

        for semester_data in requests.get(self.API_URL).json():
            formatted_start_date = arrow.get(semester_data["sNgayBatDau"], DATE_FORMAT)

            semester = Semester(
                id_=semester_data["HocKyID"],
                name=semester_data["TenHocKy"],
                term=semester_data["HocKy"],
                year=semester_data["NamHoc"],
                _start_date=formatted_start_date,
            )
            semesters.append(semester)

        semesters.sort(key=lambda semester: semester.id_)
        return semesters


class BaseScheduleGetter:
    """Base class for schedule getters handling authentication and navigation."""

    def __init__(self, student_id: str, password: str) -> None:
        """
        Initialise session, authentication, and postback form.

        Args:
            student_id (str): Student ID.
            password (str): Password.
        """
        self.session = requests.Session()
        self.auth = Auth(student_id, password)
        self.post_back_form = PostBackForm()

    def _log_in(self, return_url: str | None = "") -> Response:
        """
        Perform log in and return the resulting response.

        Args:
            return_url (str, optional): URL to redirect to after logging in.

        Returns:
            requests.Response: Response after logging in.

        Raises:
            LogInError: If logging in fails.
        """
        log_in_url = (
            f"https://stdportal.tdtu.edu.vn/Login/SignIn?ReturnURL={return_url}"
        )
        data = self.session.post(log_in_url, data=self.auth.to_form_data()).json()

        # Raise LoginError when failed, should be handled by CLI.
        if data["result"] == "fail":
            raise LogInError()

        return self.session.get(data["url"])

    def _go_to(self, url: str) -> GetterResult:
        """
        Navigate to a URL, logging in if required.

        Args:
            url (str): Target URL.

        Returns:
            GetterResult: `requests.Response` and `bs4.BeautifulSoup` from the request.
        """
        response = self.session.get(url)

        # If redirected to the log in page, log in and retry.
        if "Login" in response.url:
            self._log_in(url)
            response = self.session.get(url)

        soup = Soup(response.content, "html.parser")
        return response, soup

    def _post_back(
        self,
        url: str,
        event_target: str,
        params: dict[str, Any],
        soup: Soup | None = None,
    ) -> GetterResult:
        """
        Perform an ASP.NET postback.

        Args:
            url (str): Target URL.
            event_target (str): Value of `__EVENTTARGET`.
            params (dict[str, Any]): Additional form parameters.
            soup (bs4.BeautifulSoup, optional): Parsed HTML of the current page.

        Returns:
            GetterResult: `requests.Response` and `bs4.BeautifulSoup` from the request.
        """
        if soup:
            # __VIEWSTATE and __VIEWSTATEGENERATOR must be preserved across requests.
            self.post_back_form.viewstate = soup.find(id="__VIEWSTATE")["value"]
            self.post_back_form.viewstategenerator = soup.find(
                id="__VIEWSTATEGENERATOR"
            )["value"]

        # Construct ASP.NET postback form.
        data = {
            "__EVENTTARGET": event_target,
            **self.post_back_form.to_form_data(),
            **params,
        }
        # Submit postback.
        response = self.session.post(url, data=data)

        # If redirected to the log in page, log in and retry.
        if "Login" in response.url:
            self._log_in(url)
            response = self.session.post(url, data=data)

        soup = Soup(response.content, "html.parser")
        return response, soup


class WeeklyScheduleGetter(BaseScheduleGetter):
    """Getter for weekly schedules from the API."""

    API_URL = "https://lichhoc-lichthi.tdtu.edu.vn/tkb2.aspx"

    def _ensure_week_view(self, response: Response, soup: Soup) -> GetterResult:
        """
        Ensure the schedule is in week view.

        Args:
            response (requests.Response): Current HTTP response.
            soup (bs4.BeautifulSoup): Parsed HTML of the current page.

        Returns:
            GetterResult: `requests.Response` and `bs4.BeautifulSoup` from the request.
        """
        week_table = soup.find("table", id="ThoiKhoaBieu1_tbTKBTheoTuan")

        # If not in week view, trigger the radio button event.
        if week_table is None:
            event_target = "ThoiKhoaBieu1$radXemTKBTheoTuan"
            params = {"ThoiKhoaBieu1$radChonLua": "radXemTKBTheoTuan"}
            return self._post_back(response.url, event_target, params, soup)

        return response, soup

    def _ensure_semester_selected(
        self, response: Response, soup: Soup, semester: Semester
    ) -> GetterResult:
        """
        Ensure the given semester is selected.

        Args:
            response (requests.Response): Current HTTP response.
            soup (bs4.BeautifulSoup): Parsed HTML of the current page.
            semester (Semester): Semester to select.

        Returns:
            GetterResult: `requests.Response` and `bs4.BeautifulSoup` from the request.
        """
        semester_option = soup.find("option", value=str(semester.id_))

        # If semester is not currently selected, trigger the dropdown change event.
        if semester_option is None or not semester_option.has_attr("selected"):
            event_target = "ThoiKhoaBieu1$cboHocKy"
            params = {"ThoiKhoaBieu1$cboHocKy": semester.id_}
            return self._post_back(response.url, event_target, params, soup)

        return response, soup

    def _parse_week_range(self, soup: Soup) -> tuple[arrow.Arrow, arrow.Arrow]:
        """
        Parse start and end dates of the current week.

        Args:
            soup (bs4.BeautifulSoup): Parsed HTML of the current page.

        Returns:
            tuple[arrow.Arrow, arrow.Arrow]: Start and end dates.
        """
        date_input = soup.find("input", id="ThoiKhoaBieu1_btnTuanHienTai")
        start_date, end_date = date_input["value"].split(" - ")
        return arrow.get(start_date, DATE_FORMAT), arrow.get(end_date, DATE_FORMAT)

    def _calculate_week_presses(
        self, start_date: arrow.Arrow, end_date: arrow.Arrow, custom_date: arrow.Arrow
    ) -> tuple[str, int]:
        """
        Determine which navigation button to press and how many times to reach the custom date.

        Args:
            start_date (arrow.Arrow): Start date of the week.
            end_date (arrow.Arrow): End date of the week.
            custom_date (arrow.Arrow): Target date.

        Returns:
            tuple[str, int]: Button suffix ("Truoc" or "Sau") and number of presses.
        """
        # If custom date is before the current week, go backward.
        if custom_date < start_date:
            btn_suffix = "Truoc"
            n_presses = (start_date - custom_date).days // 7
        else:
            # Otherwise, go forward.
            btn_suffix = "Sau"
            n_presses = (custom_date - end_date).days // 7
        return btn_suffix, n_presses

    def _go_to_week(
        self, response: Response, soup: Soup, custom_date: arrow.Arrow
    ) -> GetterResult:
        """
        Navigate to the week containing the custom date.

        Args:
            response (requests.Response): Current HTTP response.
            soup (bs4.BeautifulSoup): Parsed HTML of the current page.
            custom_date (arrow.Arrow): Target date.

        Returns:
            GetterResult: `requests.Response` and `bs4.BeautifulSoup` from the request.
        """
        # Get start and end dates.
        start_date, end_date = self._parse_week_range(soup)

        # Early return if custom date is already within the given week.
        if start_date <= custom_date <= end_date:
            return response, soup

        # Get the button suffix and number of presses.
        btn_suffix, n_presses = self._calculate_week_presses(
            start_date, end_date, custom_date
        )

        # Keep pressing until the target week is reached or navigation stalls.
        prev_start_date = start_date
        for _ in range(n_presses):
            response, soup = self._post_back(
                response.url, "", {f"ThoiKhoaBieu1$btnTuan{btn_suffix}": ""}
            )
            start_date, end_date = self._parse_week_range(soup)
            # Stop if reached the correct week or navigation no longer advances.
            if start_date <= custom_date <= end_date or prev_start_date == start_date:
                break
            prev_start_date = start_date

        return response, soup

    def _parse_entry(self, td: Tag, row: int, col: int) -> Entry:
        """
        Parse a single schedule table item into an entry/class.

        Args:
            td (bs4.element.Tag): Table item containing entry data.
            row (int): Row index in the table.
            col (int): Column index in the table.

        Returns:
            Entry: A parsed schedule entry.
        """
        # Split content by <br/> and clean up the HTML tags.
        raw_lines = td.decode_contents().split("<br/>")
        data = [Soup(line, "html.parser").text.strip() for line in raw_lines]

        # Extract course_id, group and sub_group using regex.
        match = re.match(
            r"\((?P<course_id>\w*) - Nhóm\|Groups: (?P<group>\d*)(?: - Tổ\|Sub-group: )?(?P<sub_group>\d*)\)",
            data[2],
        )

        return Entry(
            course_id=match.group("course_id"),
            course_name={"vi": data[0], "en": data[1].replace("|", "")},
            room=data[3].replace("Phòng|Room: ", ""),
            weekday=col + 1,  # Column index -> day of week
            start_period=row + 1,  # Row index -> starting period
            n_periods=int(td["rowspan"]),  # Row span -> Number of periods
            group=match.group("group"),
            sub_group=match.group("sub_group"),
            is_absent="GV báo vắng" in data,
        )

    def _parse_entries(self, soup: Soup) -> list[Entry]:
        """
        Parse all entries from the schedule table.

        Args:
            soup (bs4.BeautifulSoup): Parsed HTML of the schedule page.

        Returns:
            list[Entry]: List of parsed schedule entries.
        """
        week_table = soup.find("table", id="ThoiKhoaBieu1_tbTKBTheoTuan")
        entries = []

        # Each row is a period.
        for row, tr in enumerate(week_table.find_all("tr", class_="rowContent")):
            for col, td in enumerate(tr.find_all("td", class_="cell")):
                # Skip empty item by checking the rowspan attribute.
                if not td.has_attr("rowspan"):
                    continue

                entry = self._parse_entry(td, row, col)
                entries.append(entry)

        return entries

    def get(
        self, semester: Semester, custom_date: arrow.Arrow | None = None
    ) -> Schedule:
        """
        Retrieve the weekly schedule given a semester and a custom date.

        Args:
            semester (Semester): Semester to retrieve.
            custom_date (arrow.Arrow): Date to view. Defaults to today.

        Returns:
            Schedule: Weekly schedule including entries, start and end dates.
        """
        if custom_date is None:
            custom_date = arrow.now()

        response, soup = self._go_to(self.API_URL)

        response, soup = self._ensure_week_view(response, soup)
        response, soup = self._ensure_semester_selected(response, soup, semester)
        response, soup = self._go_to_week(response, soup, custom_date)

        start_date, end_date = self._parse_week_range(soup)
        return Schedule(
            semester,
            start_date,
            end_date,
            entries=self._parse_entries(soup),
        )
