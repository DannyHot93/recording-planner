import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from html import escape

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SITE_DIR = os.path.join(BASE_DIR, "docs")
SCHEDULE_PATH = os.path.join(DATA_DIR, "schedule.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SITE_DIR, exist_ok=True)

if not os.path.exists(SCHEDULE_PATH):
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_date(value: str) -> str:
    if not value or not isinstance(value, str):
        return ""

    value = value.strip()
    value = value.replace(".", "-").replace("/", "-").replace("년", "-").replace("월", "-").replace("일", "")
    value = value.replace(" ", "")

    candidates = [
        "%Y-%m-%d",
        "%y-%m-%d",
        "%Y-%m-%d-",
        "%y-%m-%d-",
    ]

    for fmt in candidates:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 8:
        try:
            dt = datetime.strptime(digits, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return ""


def normalize_text(value: str) -> str:
    if not value:
        return ""
    return str(value).strip()


def validate_item(raw: dict) -> dict:
    item = {
        "program": normalize_text(raw.get("program", "")),
        "recording_date": normalize_date(normalize_text(raw.get("recording_date", ""))),
        "meeting_time": normalize_text(raw.get("meeting_time", "")),
        "recording_time": normalize_text(raw.get("recording_time", "")),
        "location": normalize_text(raw.get("location", "")),
        "notes": normalize_text(raw.get("notes", "")),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    meaningful = any([
        item["program"],
        item["recording_date"],
        item["location"],
        item["meeting_time"],
        item["recording_time"],
        item["notes"],
    ])

    if not meaningful:
        raise ValueError("유의미한 필드가 없음")

    return item


def remove_duplicates(data: list, new_item: dict) -> list:
    result = []
    for item in data:
        same_key = (
            item.get("program", "") == new_item.get("program", "")
            and item.get("recording_date", "") == new_item.get("recording_date", "")
            and item.get("location", "") == new_item.get("location", "")
        )
        if not same_key:
            result.append(item)

    result.append(new_item)
    return result


def cleanup_old(data: list) -> list:
    today = datetime.today().date()
    cutoff = today - timedelta(days=7)

    kept = []
    for item in data:
        d = item.get("recording_date", "")
        if not d:
            kept.append(item)
            continue

        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            if dt >= cutoff:
                kept.append(item)
        except Exception:
            kept.append(item)

    return kept


def sort_items(data: list) -> list:
    return sorted(data, key=lambda x: (x.get("recording_date", "9999-99-99"), x.get("meeting_time", "")))


def build_html(data: list):
    rows = []

    for item in sort_items(data):
        rows.append(f"""
        <tr>
          <td>{escape(item.get("recording_date", ""))}</td>
          <td>{escape(item.get("program", ""))}</td>
          <td>{escape(item.get("meeting_time", ""))}</td>
          <td>{escape(item.get("recording_time", ""))}</td>
          <td>{escape(item.get("location", ""))}</td>
          <td>{escape(item.get("notes", ""))}</td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>주간 녹화 계획표</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 24px;
      background: #f6f7f9;
      color: #111;
    }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{
      color: #666;
      margin-bottom: 20px;
      font-size: 14px;
    }}
    .wrap {{
      background: #fff;
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 780px;
    }}
    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid #e8e8e8;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #fafafa; }}
  </style>
</head>
<body>
  <h1>주간 녹화 계획표</h1>
  <div class="meta">마지막 업데이트: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
  <div class="wrap">
    <table>
      <thead>
        <tr>
          <th>녹화일</th>
          <th>프로그램</th>
          <th>집합시간</th>
          <th>녹화시간</th>
          <th>장소</th>
          <th>비고</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows) if rows else '<tr><td colspan="6">등록된 일정이 없습니다.</td></tr>'}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    out_path = os.path.join(SITE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def git_push():
    try:
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Update schedule"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)
        return True, "git push 성공"
    except Exception as e:
        return False, f"git push 실패: {e}"


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/update_schedule.py incoming/latest_schedule.json")
        sys.exit(1)

    input_path = sys.argv[1]
    raw = load_json(input_path)
    new_item = validate_item(raw)

    data = load_json(SCHEDULE_PATH)
    data = remove_duplicates(data, new_item)
    data = cleanup_old(data)
    data = sort_items(data)

    save_json(SCHEDULE_PATH, data)
    build_html(data)

    ok, msg = git_push()
    print(msg)


if __name__ == "__main__":
    main()
