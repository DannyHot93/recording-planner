import os
import sys
import json
import subprocess
from datetime import datetime, timedelta

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
        "action": normalize_text(raw.get("action", "")).lower(),
        "program": normalize_text(raw.get("program", "")),
        "recording_date": normalize_date(normalize_text(raw.get("recording_date", ""))),
        "recording_time": normalize_text(raw.get("recording_time", "")),
        "location": normalize_text(raw.get("location", "")),
        "notes": normalize_text(raw.get("notes", "")),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    meaningful = any([
        item["program"],
        item["recording_date"],
        item["recording_time"],
        item["location"],
        item["notes"],
    ])

    if not meaningful:
        raise ValueError("유의미한 필드가 없음")

    return item


def merge_items(old_item: dict, new_item: dict) -> dict:
    merged = dict(old_item)

    for key in ["program", "recording_date", "recording_time", "location", "notes"]:
        new_value = new_item.get(key, "")
        old_value = old_item.get(key, "")

        if new_value != "":
            merged[key] = new_value
        else:
            merged[key] = old_value

    merged["created_at"] = datetime.now().isoformat(timespec="seconds")
    return merged


def is_same_schedule(old_item: dict, new_item: dict) -> bool:
    old_program = old_item.get("program", "").strip()
    new_program = new_item.get("program", "").strip()
    old_location = old_item.get("location", "").strip()
    new_location = new_item.get("location", "").strip()
    old_date = old_item.get("recording_date", "").strip()
    new_date = new_item.get("recording_date", "").strip()

    if old_program and new_program and old_location and new_location and old_date and new_date:
        return (
            old_program == new_program and
            old_location == new_location and
            old_date == new_date
        )

    return False


def should_delete(item: dict, target: dict) -> bool:
    item_program = item.get("program", "").strip()
    item_date = item.get("recording_date", "").strip()
    item_location = item.get("location", "").strip()

    target_program = target.get("program", "").strip()
    target_date = target.get("recording_date", "").strip()
    target_location = target.get("location", "").strip()

    if not target_program:
        return False

    if item_program != target_program:
        return False

    if not target_date and not target_location:
        return True

    if target_date and target_location:
        return item_date == target_date and item_location == target_location

    if target_date and not target_location:
        return item_date == target_date

    if target_location and not target_date:
        return item_location == target_location

    return False


def upsert_schedule(data: list, new_item: dict) -> list:
    updated = []
    matched = False

    for item in data:
        if is_same_schedule(item, new_item):
            updated.append(merge_items(item, new_item))
            matched = True
        else:
            updated.append(item)

    if not matched:
        clean_item = dict(new_item)
        clean_item.pop("action", None)
        updated.append(clean_item)

    return updated


def delete_schedule(data: list, target_item: dict) -> list:
    updated = []
    deleted_count = 0

    for item in data:
        if should_delete(item, target_item):
            deleted_count += 1
            continue
        updated.append(item)

    print(f"삭제된 일정 수: {deleted_count}")
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
        key=lambda x: (x.get("recording_date", "9999-99-99"), x.get("recording_time", ""), x.get("program", ""))
    )


def build_html(data: list):
    schedule_json = json.dumps(data, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>주간 녹화 계획표</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 20px;
      background: #000;
      color: #f5f5f5;
      font-size: 17px;
    }}
    h1 {{
      margin-top: 0;
      margin-bottom: 12px;
      font-size: 34px;
      line-height: 1.2;
      color: #fff;
    }}
    h2 {{
      margin-top: 24px;
      margin-bottom: 14px;
      font-size: 26px;
      line-height: 1.25;
      color: #fff;
    }}
    .week-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 16px;
    }}
    .day-cell {{
      background: #ffffff;
      color: #111;
      border-radius: 16px;
      padding: 16px;
      min-height: 260px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      border: 2px solid transparent;
    }}
    .day-cell.today {{
      border-color: #2563eb;
      box-shadow: 0 4px 16px rgba(37, 99, 235, 0.25);
      background: #eef5ff;
    }}
    .day-cell.weekend {{
      background: #fcfcfd;
    }}
    .day-cell.weekend .weekday,
    .day-cell.weekend .date,
    .day-cell.weekend .program,
    .day-cell.weekend .time,
    .day-cell.weekend .location,
    .day-cell.weekend .notes,
    .day-cell.weekend .empty,
    .day-cell.weekend .schedule-detail {{
      color: #c62828;
    }}
    .day-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid #ececec;
    }}
    .weekday {{
      font-size: 21px;
      font-weight: 800;
    }}
    .date {{
      font-size: 19px;
      font-weight: 700;
      color: #555;
    }}
    .schedule-card {{
      background: #f8fafc;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 12px;
      border: 1px solid #e5e7eb;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .schedule-card:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(0,0,0,0.10);
    }}
    .program {{
      font-weight: 800;
      font-size: 17px;
      margin-bottom: 8px;
      line-height: 1.35;
    }}
    .time, .location, .notes {{
      font-size: 15px;
      margin-bottom: 6px;
      color: #333;
      line-height: 1.5;
      word-break: break-word;
    }}
    .time {{
      font-weight: 800;
      font-size: 22px;
    }}
    .schedule-detail {{
      display: none;
      margin-top: 8px;
    }}
    .schedule-card:hover .schedule-detail {{
      display: block;
    }}
    .empty {{
      font-size: 15px;
      color: #999;
      padding: 8px 0;
    }}
    .manual-duty-box {{
      margin-top: 12px;
      padding: 12px;
      border: 1px dashed #cbd5e1;
      border-radius: 12px;
      background: #fffdf7;
    }}
    .manual-duty-title {{
      font-size: 16px;
      font-weight: 800;
      margin-bottom: 8px;
      color: #111;
    }}
    .manual-duty-fixed {{
      font-size: 15px;
      margin-bottom: 10px;
      color: #444;
    }}
    .manual-duty-input {{
      width: 100%;
      box-sizing: border-box;
      padding: 10px 12px;
      border: 1px solid #d1d5db;
      border-radius: 10px;
      font-size: 15px;
      margin-bottom: 10px;
      background: #fff;
      color: #111;
    }}
    .manual-duty-button {{
      width: 100%;
      border: 0;
      border-radius: 10px;
      padding: 11px 12px;
      font-size: 15px;
      font-weight: 800;
      cursor: pointer;
      background: #111827;
      color: white;
    }}
    .manual-duty-status {{
      margin-top: 8px;
      font-size: 13px;
      color: #555;
      line-height: 1.4;
    }}
    .manual-duty-preview-card {{
      margin-top: 10px;
      background: #eef6ff;
      border: 1px solid #bfdbfe;
      border-radius: 12px;
      padding: 10px;
    }}
    .manual-duty-preview-title {{
      font-size: 16px;
      font-weight: 800;
      margin-bottom: 6px;
      color: #111;
    }}
    .manual-duty-preview-line {{
      font-size: 15px;
      color: #333;
      margin-bottom: 5px;
      line-height: 1.45;
    }}
    .other-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 16px;
    }}
    .other-day-card {{
      background: #ffffff;
      color: #111;
      border-radius: 16px;
      padding: 16px;
      min-height: 220px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      border: 1px solid #e5e7eb;
    }}
    .other-day-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid #ececec;
    }}
    .other-weekday {{
      font-size: 20px;
      font-weight: 800;
    }}
    .other-date {{
      font-size: 17px;
      font-weight: 700;
      color: #555;
    }}
    .other-day-card.weekend .other-weekday,
    .other-day-card.weekend .other-date,
    .other-day-card.weekend .program,
    .other-day-card.weekend .time,
    .other-day-card.weekend .location,
    .other-day-card.weekend .notes,
    .other-day-card.weekend .empty {{
      color: #c62828;
    }}
    @media (max-width: 1400px) {{
      .week-grid, .other-grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}
    @media (max-width: 800px) {{
      .week-grid, .other-grid {{
        grid-template-columns: 1fr;
      }}
      body {{
        font-size: 16px;
      }}
      h1 {{
        font-size: 30px;
      }}
    }}
  </style>
</head>
<body>
  <h1>주간 녹화 계획표</h1>

  <h2>이번 주 일정</h2>
  <div class="week-grid" id="week-grid"></div>

  <h2>다른 주 일정</h2>
  <div class="other-grid" id="other-grid"></div>

  <script>
    const SCHEDULE_DATA = {schedule_json};

    (function () {{
      const weekdayNames = ["월", "화", "수", "목", "금", "토", "일"];
      const pad = (n) => String(n).padStart(2, "0");

      const now = new Date();
      const formatDate = (d) =>
        `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}}`;

      const monday = new Date(now);
      const dayOfWeek = now.getDay();
      const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
      monday.setDate(now.getDate() + diffToMonday);
      monday.setHours(0, 0, 0, 0);

      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);

      const weekGrid = document.getElementById("week-grid");
      const otherGrid = document.getElementById("other-grid");

      function escapeHtml(str) {{
        return String(str || "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }}

      function getWeekdayInfo(dateStr) {{
        const d = new Date(dateStr + "T00:00:00");
        if (isNaN(d)) return null;
        const jsDay = d.getDay();
        const weekdayIndex = jsDay === 0 ? 6 : jsDay - 1;
        return {{
          dateObj: d,
          weekdayIndex,
          weekdayKor: weekdayNames[weekdayIndex],
          isWeekend: weekdayIndex >= 5
        }};
      }}

      function getWeekSortKey(dateStr) {{
        const info = getWeekdayInfo(dateStr);
        if (!info) return [9999, 99, 99];

        const d = info.dateObj;
        const dayNum = d.getDay() === 0 ? 7 : d.getDay();
        const thursday = new Date(d);
        thursday.setDate(d.getDate() + (4 - dayNum));

        const yearStart = new Date(thursday.getFullYear(), 0, 1);
        const week = Math.ceil((((thursday - yearStart) / 86400000) + 1) / 7);
        return [thursday.getFullYear(), week, dayNum];
      }}

      const weekDates = [];
      for (let i = 0; i < 7; i++) {{
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        weekDates.push(d);
      }}

      const groupedThisWeek = {{}};
      weekDates.forEach(d => groupedThisWeek[formatDate(d)] = []);

      const futureOtherItems = [];

      (SCHEDULE_DATA || []).forEach(item => {{
        const rd = item.recording_date || "";
        if (!rd) return;

        if (groupedThisWeek[rd]) {{
          groupedThisWeek[rd].push(item);
          return;
        }}

        if (rd < formatDate(monday)) {{
          return;
        }}

        futureOtherItems.push(item);
      }});

      weekDates.forEach((d, i) => {{
        const dateStr = formatDate(d);
        const items = (groupedThisWeek[dateStr] || []).sort((a, b) => {{
          const t1 = a.recording_time || "";
          const t2 = b.recording_time || "";
          if (t1 !== t2) return t1.localeCompare(t2);
          return (a.program || "").localeCompare(b.program || "");
        }});

        const isToday = dateStr === formatDate(now);
        const isWeekend = i >= 5;

        const cards = items.length
          ? items.map(item => `
              <div class="schedule-card">
                <div class="program">${{escapeHtml(item.program)}}</div>
                <div class="time">시간: ${{escapeHtml(item.recording_time || "-")}}</div>
                <div class="schedule-detail">
                  <div class="location">장소: ${{escapeHtml(item.location || "-")}}</div>
                  <div class="notes">비고: ${{escapeHtml(item.notes || "-")}}</div>
                </div>
              </div>
            `).join("")
          : '<div class="empty">일정 없음</div>';

        let sundayManual = "";
        if (i === 6) {{
          sundayManual = `
            <div class="manual-duty-box">
              <div class="manual-duty-title">뉴스데스크 근무자 입력</div>
              <div class="manual-duty-fixed">업무: 뉴스데스크</div>
              <input id="manual-duty-name" class="manual-duty-input" type="text" placeholder="근무자 이름 입력">
              <button id="manual-duty-save" class="manual-duty-button">저장</button>
              <div id="manual-duty-status" class="manual-duty-status"></div>
              <div id="manual-duty-preview"></div>
            </div>
          `;
        }}

        const cell = document.createElement("div");
        cell.className = "day-cell" + (isToday ? " today" : "") + (isWeekend ? " weekend" : "");
        cell.innerHTML = `
          <div class="day-header">
            <div class="weekday">${{weekdayNames[i]}}</div>
            <div class="date">${{pad(d.getMonth() + 1)}}/${{pad(d.getDate())}}</div>
          </div>
          <div class="day-body">
            ${{cards}}
            ${{sundayManual}}
          </div>
        `;
        weekGrid.appendChild(cell);
      }});

      const groupedOtherByWeekday = [[], [], [], [], [], [], []];

      futureOtherItems.sort((a, b) => {{
        const k1 = getWeekSortKey(a.recording_date || "");
        const k2 = getWeekSortKey(b.recording_date || "");

        for (let i = 0; i < 3; i++) {{
          if (k1[i] !== k2[i]) return k1[i] - k2[i];
        }}

        const t1 = a.recording_time || "";
        const t2 = b.recording_time || "";
        if (t1 !== t2) return t1.localeCompare(t2);

        return (a.program || "").localeCompare(b.program || "");
      }});

      futureOtherItems.forEach(item => {{
        const info = getWeekdayInfo(item.recording_date || "");
        if (!info) return;
        groupedOtherByWeekday[info.weekdayIndex].push(item);
      }});

      for (let i = 0; i < 7; i++) {{
        const isWeekend = i >= 5;
        const items = groupedOtherByWeekday[i];

        const cards = items.length
          ? items.map(item => `
              <div class="schedule-card">
                <div class="program">${{escapeHtml(item.program)}}</div>
                <div class="time">시간: ${{escapeHtml(item.recording_time || "-")}}</div>
                <div class="location">장소: ${{escapeHtml(item.location || "-")}}</div>
                <div class="notes">비고: ${{escapeHtml(item.notes || "-")}}</div>
              </div>
            `).join("")
          : '<div class="empty">일정 없음</div>';

        const card = document.createElement("div");
        card.className = "other-day-card" + (isWeekend ? " weekend" : "");
        card.innerHTML = `
          <div class="other-day-header">
            <div class="other-weekday">${{weekdayNames[i]}}</div>
            <div class="other-date">다른 주</div>
          </div>
          <div class="other-day-body">
            ${{cards}}
          </div>
        `;
        otherGrid.appendChild(card);
      }});

      const sundayKey = `newsdesk-duty-${{formatDate(sunday)}}`;
      const nameInput = document.getElementById("manual-duty-name");
      const saveButton = document.getElementById("manual-duty-save");
      const statusEl = document.getElementById("manual-duty-status");
      const previewEl = document.getElementById("manual-duty-preview");

      function renderDutyPreview(name) {{
        if (!previewEl) return;

        if (!name) {{
          previewEl.innerHTML = "";
          return;
        }}

        previewEl.innerHTML = `
          <div class="manual-duty-preview-card">
            <div class="manual-duty-preview-title">수기 입력 일정</div>
            <div class="manual-duty-preview-line">업무: 뉴스데스크</div>
            <div class="manual-duty-preview-line">날짜: ${{formatDate(sunday)}} (일)</div>
            <div class="manual-duty-preview-line">근무자: ${{escapeHtml(name)}}</div>
          </div>
        `;
      }}

      const savedName = localStorage.getItem(sundayKey) || "";
      if (nameInput) nameInput.value = savedName;
      renderDutyPreview(savedName);

      if (saveButton) {{
        saveButton.addEventListener("click", function () {{
          const value = (nameInput?.value || "").trim();

          if (!value) {{
            if (statusEl) statusEl.textContent = "근무자 이름을 입력해 주세요.";
            renderDutyPreview("");
            return;
          }}

          localStorage.setItem(sundayKey, value);
          if (statusEl) statusEl.textContent = "이 브라우저에 저장되었습니다.";
          renderDutyPreview(value);
        }});
      }}
    }})();
  </script>
</body>
</html>
"""
    out_path = os.path.join(SITE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def git_push():
    try:
        subprocess.run(["git", "pull", "--no-rebase", "origin", "main"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True)

        commit_result = subprocess.run(
            ["git", "commit", "-m", "Update schedule"],
            cwd=BASE_DIR,
            check=False,
            capture_output=True,
            text=True
        )

        combined_output = (commit_result.stdout or "") + (commit_result.stderr or "")
        nothing_to_commit = "nothing to commit" in combined_output.lower()

        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)

        if nothing_to_commit:
            return True, "변경 없음, git push 확인 완료"
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

    if new_item.get("action") == "delete":
        data = delete_schedule(data, new_item)
    else:
        data = upsert_schedule(data, new_item)

    cleaned = []
    for item in data:
        new_clean = dict(item)
        new_clean.pop("action", None)
        cleaned.append(new_clean)

    cleaned = cleanup_old(cleaned)
    cleaned = sort_items(cleaned)

    save_json(SCHEDULE_PATH, cleaned)
    build_html(cleaned)

    ok, msg = git_push()
    print(msg)


if __name__ == "__main__":
    main()
