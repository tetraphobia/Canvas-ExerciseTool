# Canvas Exercise Grader

Fetches every student's **full submission history** for all assignments in the "Exercises" group, applies the correct grading policy, and exports a Canvas-compatible gradebook CSV ready for manual import.

## Prerequisites
- Python 3.7+
- [requests](https://pypi.org/project/requests/) (`pip install requests`)

## Configuration

Set the following environment variables before running:

| Variable | Description |
|----------|-------------|
| `CANVAS_BASE_URL` | Base URL of your Canvas instance, e.g. `https://instructure.charlotte.edu` |
| `CANVAS_TOKEN` | Canvas API access token (Account → Settings → New Access Token) |
| `CANVAS_COURSE_ID` | Numeric ID of the course (visible in the course URL) |

## Usage

```sh
export CANVAS_BASE_URL="https://instructure.charlotte.edu"
export CANVAS_TOKEN="1234~your_token_here"
export CANVAS_COURSE_ID="98765"

python grader.py
```

The script prints progress as it runs and writes **`grades_updated.csv`** in the current directory when finished.

## Importing the CSV into Canvas

1. Open your course in Canvas and go to **Grades**.
2. Click **Actions → Import**.
3. Upload `grades_updated.csv`.
4. Review the preview and confirm the import.
