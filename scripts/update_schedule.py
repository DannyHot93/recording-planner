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
    value = value.replace(".", "-").replace("/", "-")
    value = value.replace("년", "-").replace("월", "-").replace("일", "")
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


def merge_items(old_item: dict, new_item: dict) -> dict:
    """
    새 값이 빈 문자열이 아니면 새 값으로 덮어쓰고,
    새 값이 비어 있으면 기존 값을 유지.
    """
    merged = dict(old_item)

    for key in ["program", "recording_date", "meeting_time", "recording_time", "location", "notes"]:
        new_value = new_item.get(key, "")
        old_value = old_item.get(key, "")

        if new_value != "":
            merged[key] = new_value
        else:
            merged[key] = old_value

    merged["created_at"] = datetime.now().isoformat(timespec="seconds")
    return merged


def is_same_schedule(old_item: dict, new_item: dict) -> bool:
    """
    같은 일정인지 판별하는 개선 로직.

    우선순위:
    1) program + location 이 같으면 같은 일정 후보
    2) 추가로 시간이 일부라도 맞으면 더 강하게 같은 일정으로 판단
    3) 날짜 수정 요청에도 기존 일정으로 인식할 수 있도록 recording_date는
       동일 판별의 필수 조건으로 사용하지 않음
    """
    old_program = old_item.get("program", "").strip()
    new_program = new_item.get("program", "").strip()
    old_location = old_item.get("location", "").strip()
    new_location = new_item.get("location", "").strip()

    old_meeting = old_item.get("meeting_time", "").strip()
    new_meeting = new_item.get("meeting_time", "").strip()
    old_recording = old_item.get("recording_time", "").strip()
    new_recording = new_item.get("recording_time", "").strip()

    # 프로그램명과 장소가 모두 있으면 이 둘을 가장 강한 기준으로 사용
    if old_program and new_program and old_location and new_location:
        if old_program == new_program and old_location == new_location:
            return True

    # 프로그램명만 같고, 시간 일부라도 같으면 같은 일정으로 판단
    if old_program and new_program and old_program == new_program:
        if old_meeting and new_meeting and old_meeting == new_meeting:
            return True
        if old_recording and new_recording and old_recording == new_recording:
            return True

    # 장소만 같고 프로그램도 비슷하게 들어온 경우 대비
    if old_location and new_location and old_location == new_location:
        if old_program and new_program and old_program == new_program:
            return True

    return False


def upsert_schedule(data: list, new_item: dict) -> list:
    """
    기존 일정 중 같은 일정이 있으면 병합해서 업데이트,
    없으면 새로 추가.
    """
    updated = []
    matched = False

    for item in data:
        if is_same_schedule(item, new_item):
            merged = merge_items(item, new_item)
            updated.append(merged)
            matched = True
        else:
            updated.append(item)

    if not matched:
        updated.append(new_item)

    return updated


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
    return sorted(
        data,
        key=lambda x: (x.get("recording_date", "9999-99-99"), x.get("meeting_time", ""))
    )


def build_html(data: list):
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())  # 월요일
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    grouped_this_week = {d.strftime("%Y-%m-%d"): [] for d in week_dates}
    other_items = []

    for item in data:
        rd = item.get("recording_date", "")
        if rd in grouped_this_week:
            grouped_this_week[rd].append(item)
        else:
            other_items.append(item)

    day_cells = []
    for i, d in enumerate(week_dates):
        d_str = d.strftime("%Y-%m-%d")
        items = grouped_this_week.get(d_str, [])

        cards = []
        for item in items:
            cards.append(f"""
            <div class="schedule-card">
              <div class="program">{escape(item.get("program", ""))}</div>
              <div class="time">집합: {escape(item.get("meeting_time", "")) or '-'}</div>
              <div class="time">녹화: {escape(item.get("recording_time", "")) or '-'}</div>
              <div class="location">장소: {escape(item.get("location", "")) or '-'}</div>
              <div class="notes">비고: {escape(item.get("notes", "")) or '-'}</div>
            </div>
            """)

        is_today = d == today
        is_weekend = i >= 5

        cell_class = "day-cell"
        if is_today:
            cell_class += " today"
        if is_weekend:
            cell_class += " weekend"

        day_cells.append(f"""
        <div class="{cell_class}">
          <div class="day-header">
            <div class="weekday">{weekday_names[i]}</div>
            <div class="date">{d.strftime("%m/%d")}</div>
          </div>
          <div class="day-body">
            {''.join(cards) if cards else '<div class="empty">일정 없음</div>'}
          </div>
        </div>
        """)

    other_items = sorted(
        other_items,
        key=lambda x: (x.get("recording_date", "9999-99-99"), x.get("meeting_time", ""))
    )

    other_rows = []
    for item in other_items:
        other_rows.append(f"""
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
      background: #f4f6f8;
      color: #111;
    }}

    h1 {{
      margin-bottom: 6px;
    }}

    h2 {{
      margin-top: 36px;
      margin-bottom: 12px;
      font-size: 22px;
    }}

    .meta {{
      color: #666;
      margin-bottom: 20px;
      font-size: 14px;
      line-height: 1.5;
    }}

    .week-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 14px;
    }}

    .day-cell {{
      background: white;
      border-radius: 16px;
      padding: 14px;
      min-height: 260px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
      border: 2px solid transparent;
    }}

    .today {{
      border-color: #2563eb;
      box-shadow: 0 4px 16px rgba(37, 99, 235, 0.18);
      background: #eef5ff;
    }}

    .weekend {{
      background: #fcfcfd;
    }}

    .day-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #ececec;
    }}

    .weekday {{
      font-size: 18px;
      font-weight: 700;
    }}

    .date {{
      font-size: 14px;
      color: #666;
    }}

    .schedule-card {{
      background: #f8fafc;
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
      border: 1px solid #e5e7eb;
    }}

    .program {{
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 6px;
    }}

    .time, .location, .notes {{
      font-size: 13px;
      margin-bottom: 4px;
      color: #333;
      line-height: 1.4;
      word-break: break-word;
    }}

    .empty {{
      font-size: 13px;
      color: #999;
      padding: 8px 0;
    }}

    .list-wrap {{
      background: white;
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
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
      font-size: 14px;
    }}

    th {{
      background: #fafafa;
    }}

    @media (max-width: 1200px) {{
      .week-grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}

    @media (max-width: 700px) {{
      .week-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <h1>주간 녹화 계획표</h1>
  <div class="meta">
    이번 주: {week_dates[0].strftime("%Y-%m-%d")} ~ {week_dates[-1].strftime("%Y-%m-%d")}<br>
    마지막 업데이트: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
  </div>

  <h2>이번 주 일정</h2>
  <div class="week-grid">
    {''.join(day_cells)}
  </div>

  <h2>다른 주 일정</h2>
  <div class="list-wrap">
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
        {''.join(other_rows) if other_rows else '<tr><td colspan="6">다른 주 일정이 없습니다.</td></tr>'}
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
    data = upsert_schedule(data, new_item)
    data = cleanup_old(data)
    data = sort_items(data)

    save_json(SCHEDULE_PATH, data)
    build_html(data)

    ok, msg = git_push()
    print(msg)


if __name__ == "__main__":
    main()
