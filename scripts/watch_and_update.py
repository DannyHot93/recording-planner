import os
import time
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH_FILE = os.path.join(BASE_DIR, "incoming", "latest_schedule.json")
UPDATE_SCRIPT = os.path.join(BASE_DIR, "scripts", "update_schedule.py")

last_mtime = None

def file_exists_and_ready(path):
    return os.path.exists(path) and os.path.getsize(path) > 0

def run_update():
    try:
        result = subprocess.run(
            ["python3", UPDATE_SCRIPT, WATCH_FILE],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        print("===== update_schedule.py 실행 =====")
        print(result.stdout)
        if result.stderr:
            print("===== stderr =====")
            print(result.stderr)
    except Exception as e:
        print(f"실행 오류: {e}")

def main():
    global last_mtime
    print(f"감시 시작: {WATCH_FILE}")

    while True:
        try:
            if file_exists_and_ready(WATCH_FILE):
                mtime = os.path.getmtime(WATCH_FILE)

                if last_mtime is None:
                    last_mtime = mtime

                elif mtime != last_mtime:
                    print("JSON 변경 감지")
                    time.sleep(1.0)
                    run_update()
                    last_mtime = mtime

        except Exception as e:
            print(f"감시 중 오류: {e}")

        time.sleep(2)

if __name__ == "__main__":
    main()
