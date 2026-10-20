import os
import csv
import sys
from datetime import datetime, timezone
import requests

BASE_URL = os.environ["CANVAS_BASE_URL"].rstrip("/")
TOKEN = os.environ["CANVAS_TOKEN"]
COURSE_ID = os.environ["CANVAS_COURSE_ID"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
OUTPUT_FILE = "grades_updated.csv"


def paginate(url, params=None):
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        yield from resp.json()
        params = None
        link = resp.headers.get("Link", "")
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                break


def find_exercises_group():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignment_groups"
    for group in paginate(url):
        if group["name"] == "Exercises":
            return group["id"]
    print("Error: no assignment group named 'Exercises' found.", file=sys.stderr)
    sys.exit(1)


def get_assignments(group_id):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments"
    return list(paginate(url, params={"assignment_group_id": group_id, "per_page": 100}))


def get_students():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/enrollments"
    seen = {}
    for enrollment in paginate(url, params={"type[]": "StudentEnrollment", "per_page": 100}):
        uid = enrollment["user_id"]
        if uid not in seen:
            user = enrollment.get("user", {})
            seen[uid] = {
                "user_id": uid,
                "sortable_name": user.get("sortable_name", ""),
                "sis_user_id": user.get("sis_user_id") or "",
                "login_id": user.get("login_id") or "",
            }
    return sorted(seen.values(), key=lambda s: s["sortable_name"])


def get_submissions(assignment_id):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments/{assignment_id}/submissions"
    return {
        sub["user_id"]: sub
        for sub in paginate(url, params={"include[]": "submission_history", "per_page": 100})
    }


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def compute_grade(submission, due_at, points_possible):
    history = [h for h in submission.get("submission_history", []) if h.get("submitted_at")]
    if not history:
        if due_at and parse_dt(due_at) > datetime.now(timezone.utc):
            return None  # due date hasn't passed yet, leave blank
        return 0
    if due_at is None:
        return points_possible
    due = parse_dt(due_at)
    if any(parse_dt(h["submitted_at"]) <= due for h in history):
        return points_possible
    return points_possible * 0.5


def main():
    print("Fetching assignment group...")
    group_id = find_exercises_group()

    print("Fetching assignments...")
    assignments = get_assignments(group_id)
    print(f"  {len(assignments)} assignment(s) found")

    print("Fetching students...")
    students = get_students()
    print(f"  {len(students)} student(s) found")

    grades = {s["user_id"]: {} for s in students}

    for assignment in assignments:
        aid = assignment["id"]
        due_at = assignment.get("due_at")
        points_possible = assignment.get("points_possible") or 0
        print(f"Processing submissions: {assignment['name']}")
        submissions = get_submissions(aid)
        for student in students:
            uid = student["user_id"]
            grades[uid][aid] = compute_grade(submissions.get(uid, {}), due_at, points_possible)

    fieldnames = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section"]
    for a in assignments:
        fieldnames.append(f"{a['name']} ({a['id']})")

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for student in students:
            uid = student["user_id"]
            row = {
                "Student": student["sortable_name"],
                "ID": uid,
                "SIS User ID": student["sis_user_id"],
                "SIS Login ID": student["login_id"],
                "Section": "",
            }
            for a in assignments:
                g = grades[uid][a["id"]]
                row[f"{a['name']} ({a['id']})"] = "" if g is None else (int(g) if g == int(g) else g)
            writer.writerow(row)

    print(f"\nWrote {OUTPUT_FILE} ({len(students)} students x {len(assignments)} assignments)")


if __name__ == "__main__":
    main()
