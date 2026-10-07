"""
อ่าน due_soon.json (งานที่เหลือเวลาส่งไม่เกิน 8 ชม.) เทียบกับ notified.json
(งานที่เคยแจ้งไปแล้ว) เพื่อหา "งานใหม่" ที่ต้องส่งอีเมลแจ้งเตือน
แล้วเขียนเนื้อหาอีเมลลง mail_body.txt + อัปเดต notified.json
รันโดย GitHub Actions หลังจาก tryapi.py เสมอ
"""
import json
import os
from datetime import datetime
import pytz

bkk_tz = pytz.timezone('Asia/Bangkok')
now = datetime.now(bkk_tz)


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


due_soon = load_json('due_soon.json', [])
notified = load_json('notified.json', {})  # {activity_id: due_iso}

new_tasks = [t for t in due_soon if str(t.get('id')) not in notified]

if new_tasks:
    lines = ['งานใกล้ถึงกำหนดส่งใน 8 ชั่วโมง:\n']
    for t in new_tasks:
        lines.append(f"- [{t.get('subject')}] {t.get('title')}")
        lines.append(f"  กำหนดส่ง: {t.get('due')} (เวลาไทย)")
        lines.append(f"  ลิงก์ส่งงาน: {t.get('url')}\n")
    with open('mail_body.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'จะส่งอีเมลแจ้ง {len(new_tasks)} งาน')
else:
    print('ไม่มีงานใหม่ที่ต้องแจ้งเตือน')

# อัปเดตรายการที่แจ้งแล้ว + ตัดรายการที่พ้นกำหนดไปแล้วทิ้ง (กันไฟล์บวม)
due_soon_ids = {str(t.get('id')) for t in due_soon}
for t in due_soon:
    notified[str(t.get('id'))] = t.get('due_iso')
notified = {
    k: v for k, v in notified.items()
    if k in due_soon_ids or datetime.fromisoformat(v) > now
}
with open('notified.json', 'w', encoding='utf-8') as f:
    json.dump(notified, f, ensure_ascii=False, indent=2)

# ส่ง output ให้ GitHub Actions step ต่อไป
gh_output = os.environ.get('GITHUB_OUTPUT')
if gh_output:
    with open(gh_output, 'a', encoding='utf-8') as f:
        f.write(f"has_new={'true' if new_tasks else 'false'}\n")
        f.write(f"new_count={len(new_tasks)}\n")
