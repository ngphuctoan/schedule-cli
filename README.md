# Schedule CLI

Command-line interface to view and export week schedules.

> [!WARNING]
> - This is an unofficial project created out of personal interest. **Use at your own risk!**
> - Do **NOT** use this tool to violate the university's guidelines, the author is not responsible for any misuse or consequences.
> - The accuracy of the resulting data is not guaranteed and changes to the university's website may break this tool.

> [!TIP]
> Found any issue? [Create a new request!](https://github.com/ngphuctoan/schedule-cli/issues)

## Installation

### Releases

_(Coming soon.)_

### Manual

Clone the repository and install the necessary dependencies:

```bash
git clone https://github.com/ngphuctoan/schedule-cli.git
cd schedule-cli
pip install -e .
```

Using `-e` makes it editable so changes to the code are reflected immediately.

## Usage

Fetch available semester(s):

```bash
schedule-cli fetch-semesters
```

Set login credentials:

```bash
schedule-cli set-account --student-id STUDENT_ID --password PASSWORD
```

> [!CAUTION]
> Credentials are stored on your system using the `keyring` library. Please make sure to secure your computer with a password!

View this week's schedule:

```bash
schedule-cli view --semester-id SEMESTER_ID
```

Export schedule to `schedule.json` for a specified week:

```
schedule-cli export --semester-id SEMESTER_ID --custom-date DD/MM/YYYY --output ./schedule.json
```

## Todo

- [ ] Add GitHub actions to publish releases
- [ ] Vietnamese translation
- [ ] View/export general schedule
