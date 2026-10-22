import os
import sys
from datetime import datetime, timezone
import requests

BASE_URL = os.environ["CANVAS_BASE_URL"].rstrip("/")
TOKEN = os.environ["CANVAS_TOKEN"]
COURSE_ID = os.environ["CANVAS_COURSE_ID"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


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
            }
    return sorted(seen.values(), key=lambda s: s["sortable_name"])


def get_submissions(assignment_id):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments/{assignment_id}/submissions"
    return {
        sub["user_id"]: sub
        for sub in paginate(url, params={"include[]": "submission_history", "per_page": 100})
    }


def clear_grade(assignment_id, user_id):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments/{assignment_id}/submissions/{user_id}"
    resp = requests.put(url, headers=HEADERS, data={"submission[posted_grade]": ""})
    resp.raise_for_status()


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    print("Fetching assignment group...")
    group_id = find_exercises_group()

    print("Fetching assignments...")
    assignments = get_assignments(group_id)
    print(f"  {len(assignments)} assignment(s) found")

    print("Fetching students...")
    students = get_students()
    print(f"  {len(students)} student(s) found\n")

    now = datetime.now(timezone.utc)
    cleared = 0

    for assignment in assignments:
        due_at = assignment.get("due_at")
        if due_at is not None and parse_dt(due_at) <= now:
            continue

        aid = assignment["id"]
        submissions = get_submissions(aid)

        for student in students:
            uid = student["user_id"]
            sub = submissions.get(uid, {})
            history = [h for h in sub.get("submission_history", []) if h.get("submitted_at")]

            if not history and sub.get("score") == 0:
                print(f"Clearing: {student['sortable_name']} — {assignment['name']}")
                clear_grade(aid, uid)
                cleared += 1

    print(f"\nCleared {cleared} grade(s)")


if __name__ == "__main__":
    main()
