# Schedule CLI

Command-line interface to view and export week schedules.

## Installation

### Releases

_(Coming soon.)_

### Manual

Clone the repository and install the necessary dependencies:

```bash
git clone https://github.com/ngphuctoan/schedule-cli.git
cd schedule-cli
pip install . -e
```

Using `-e` makes it editable so changes to the code are reflected immediately.

## Usage

Fetch available semester(s):

```bash
schedule-cli fetch-semesters
```

Set log in credentials:

```bash
schedule-cli set-account --student-id STUDENT_ID --password PASSWORD
```

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
