# Schedule CLI

A command-line interface for TDTU students to view and export schedule :calendar:

> [!WARNING]
>
> - This is an unofficial project created out of personal interest. **Use at your own risk!**
> - Do **NOT** use this tool to violate TDTU's guidelines, the author is not responsible for any misuse or consequences.
> - The accuracy of the resulting data is not guaranteed and changes to the university's website may break this tool.

## Installation

Download the `.whl` or `.tar.gz` package from the [Releases](https://github.com/ngphuctoan/schedule-cli/releases) page.

Then install the file with `pip`:

```bash
pip install ./schedule_cli-X.Y.Z.whl
```

Replace `X.Y.Z` with the tag you want (e.g. `0.1.0`), and `.whl` with `.tar.gz` if you wish to use the archive.

## Development

Requirements:

- Python 3.10+ (3.13+ recommended)
- Poetry 1.8.2+

Clone the repository:

```bash
git clone https://github.com/ngphuctoan/schedule-cli.git
cd schedule-cli
```

Install the dependencies:

```bash
poetry install
```

Finally, launch the virtual environment:

```bash
poetry shell
```

## Usage

Fetch available semester(s):

```bash
schedule-cli fetch-semesters
```

View this week's schedule:

```bash
schedule-cli view --semester-id SEMESTER_ID
```

Export schedule to a JSON file at `./schedule.json` for a specified week:

```bash
schedule-cli export --semester-id SEMESTER_ID --custom-date DD/MM/YYYY --json --output ./schedule.json
```
