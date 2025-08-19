import re
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from requests import Response
from bs4 import BeautifulSoup as Soup

from schedule_cli.modules.constants import DATE_FORMAT
from schedule_cli.modules.models import Entry, Semester


class LogInError(Exception):
    pass


@dataclass
class Auth:
    student_id: str
    password: str

    def to_form_data(self) -> dict:
        return {"user": self.student_id, "pass": self.password}


@dataclass
class PostBackForm:
    _viewstate: str = ""
    _viewstategenerator: str = ""

    def to_form_data(self) -> dict:
        return {
            "__VIEWSTATE": self._viewstate,
            "__VIEWSTATEGENERATOR": self._viewstategenerator,
        }


def get_semesters() -> list[Semester]:
    API_URL = "https://thoikhoabieudukien.tdtu.edu.vn/API/XemKetQuaDangKy/LoadHocKy"
    semesters = []

    for semester_data in requests.get(API_URL).json():
        formatted_start_date = datetime.strptime(semester_data["sNgayBatDau"], DATE_FORMAT)

        semester = Semester(
            id_=semester_data["HocKyID"],
            name=semester_data["TenHocKy"],
            term=semester_data["HocKy"],
            year=semester_data["NamHoc"],
            start_date=formatted_start_date,
        )
        semesters.append(semester)

    semesters.sort(key=lambda semester: semester.id_)
    return semesters


class ScheduleGetter:
    def __init__(self, student_id: str, password: str) -> None:
        self.session = requests.Session()
        self.auth = Auth(student_id, password)
        self.post_back_form = PostBackForm()

    def _log_in(self, return_url: str = "") -> Response:
        log_in_url = f"https://stdportal.tdtu.edu.vn/Login/SignIn?ReturnURL={return_url}"
        data = self.session.post(log_in_url, data=self.auth.to_form_data()).json()
        if data["result"] == "fail":
            raise LogInError()
        return self.session.get(data["url"])

    def _go_to(self, url: str) -> tuple[Response, Soup]:
        response = self.session.get(url)
        if "Login" in response.url:
            self._log_in(url)
            response = self.session.get(url)

        soup = Soup(response.content, "html.parser")
        return response, soup

    def _post_back(self, url: str, event_target: str, params: dict, soup: Soup = None) -> tuple[Response, Soup]:
        if soup:
            self.post_back_form._viewstate = soup.find(id="__VIEWSTATE")["value"]
            self.post_back_form._viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")["value"]

        data = {
            "__EVENTTARGET": event_target,
            **self.post_back_form.to_form_data(),
            **params,
        }
        response = self.session.post(url, data=data)
        if "Login" in response.url:
            self._log_in(url)
            response = self.session.post(url, data=data)

        soup = Soup(response.content, "html.parser")
        return response, soup

    def _ensure_week_view(self, response: Response, soup: Soup) -> tuple[Response, Soup]:
        week_table = soup.find("table", id="ThoiKhoaBieu1_tbTKBTheoTuan")
        if week_table is None:
            event_target = "ThoiKhoaBieu1$radXemTKBTheoTuan"
            params = {"ThoiKhoaBieu1$radChonLua": "radXemTKBTheoTuan"}
            return self._post_back(response.url, event_target, params, soup)
        return response, soup

    def _ensure_semester_selected(self, response: Response, soup: Soup, semester: Semester) -> tuple[Response, Soup]:
        semester_option = soup.find("option", value=str(semester.id_))
        if semester_option is None or not semester_option.has_attr("selected"):
            event_target = "ThoiKhoaBieu1$cboHocKy"
            params = {"ThoiKhoaBieu1$cboHocKy": semester.id_}
            return self._post_back(response.url, event_target, params, soup)
        return response, soup

    def _parse_week_range(self, soup: Soup) -> tuple[datetime, datetime]:
        date_input = soup.find("input", id="ThoiKhoaBieu1_btnTuanHienTai")
        date_values = date_input["value"].split(" - ")
        return tuple(datetime.strptime(date_value, DATE_FORMAT) for date_value in date_values)

    def _go_to_week(self, response: Response, soup: Soup, custom_date: datetime) -> tuple[Response, Soup]:
        start_date, end_date = self._parse_week_range(soup)

        if start_date <= custom_date <= end_date:
            return response, soup

        if custom_date < start_date:
            btn_suffix = "Truoc"
            n_presses = (start_date - custom_date).days // 7
        else:
            btn_suffix = "Sau"
            n_presses = (custom_date - end_date).days // 7

        prev_start_date = start_date
        for _ in range(n_presses):
            response, soup = self._post_back(response.url, "", {f"ThoiKhoaBieu1$btnTuan{btn_suffix}": ""})

            start_date, end_date = self._parse_week_range(soup)
            if start_date <= custom_date <= end_date or prev_start_date == start_date:
                break
            prev_start_date = start_date

        return response, soup

    def _parse_entries(self, soup: Soup, start_date: datetime) -> list[Entry]:
        week_table = soup.find("table", id="ThoiKhoaBieu1_tbTKBTheoTuan")
        entries = []

        for i, row in enumerate(week_table.find_all("tr", class_="rowContent")):
            for j, item in enumerate(row.find_all("td", class_="cell")):
                if not item.has_attr("rowspan"):
                    continue

                raw_data = item.decode_contents().split("<br/>")
                entry_data = [Soup(raw_entry_data, "html.parser").text.strip() for raw_entry_data in raw_data]

                entry_info = re.match(
                    r"\((?P<course_id>\w*) - Nhóm\|Groups: (?P<group>\d*)(?: - Tổ\|Sub-group: )?(?P<sub_group>\d*)\)",
                    entry_data[2],
                )
                n_periods = int(item["rowspan"])

                entry = Entry(
                    course_id=entry_info.group("course_id"),
                    course_name=entry_data[0],
                    room=entry_data[3].replace("Phòng|Room: ", ""),
                    date=start_date + timedelta(days=j),
                    start_period=i + 1,
                    end_period=i + n_periods,
                    group=entry_info.group("group"),
                    sub_group=entry_info.group("sub_group"),
                    is_absent="GV báo vắng" in entry_data,
                )
                entries.append(entry)

        return entries

    def get_week_schedule(self, semester: Semester, custom_date: datetime = None) -> list[Entry]:
        if custom_date is None:
            custom_date = datetime.now()

        reponse, soup = self._go_to("https://lichhoc-lichthi.tdtu.edu.vn/tkb2.aspx")

        reponse, soup = self._ensure_week_view(reponse, soup)
        reponse, soup = self._ensure_semester_selected(reponse, soup, semester)
        reponse, soup = self._go_to_week(reponse, soup, custom_date)

        start_date, _ = self._parse_week_range(soup)
        return self._parse_entries(soup, start_date)
