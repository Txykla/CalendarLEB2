import requests
import os
import re
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz

# ==========================================
# ตั้งค่าเริ่มต้น & Mapping
# ==========================================
session = requests.Session()
bkk_tz = pytz.timezone('Asia/Bangkok')
now = datetime.now(bkk_tz)

class_mapping = {
    "1545560": "INC 411",
    "1557768": "INC 362",
    "1556430": "INC 351",
    "1568802": "INC 353",
    "1596682": "INC 361",
    "1575964": "MEE 224",
    "1563128": "INC 352"
}

# ==========================================
# Step 1-2: Login & สร้าง Session Cookie
# ==========================================
login_url = "https://leb2-mcs-api-production.leb2.org/public/login/v1/login"
login_payload = {
    "username": "67070508088",
    "password": os.environ.get("LEB2_PASS"), # อย่าลืมใส่รหัสผ่านจริง
    "remember": True
}
print("1. กำลัง Login ขอ Token...")
resp1 = session.post(login_url, json=login_payload)
token = resp1.json().get('token')

print("2. กำลังสร้าง Session Cookie...")
session.get(f"https://app.leb2.org/login?token={token}")

# ==========================================
# Step 3: ประมวลผลการบ้าน & สร้าง .ics
# ==========================================
student_id = "10025333"
class_ids = list(class_mapping.keys()) # ดึงรหัสจาก mapping มาวนลูปได้เลย
cal = Calendar()

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

print("3. กำลังดึงข้อมูลและกรองการบ้าน...")

for cid in class_ids:
    activities_url = f"https://app.leb2.org/api/get/assessment-activities/student?class_id={cid}&student_id={student_id}&filter_groups%5B0%5D%5Bfilters%5D%5B0%5D%5Bkey%5D=class_id&filter_groups%5B0%5D%5Bfilters%5D%5B0%5D%5Bvalue%5D={cid}&sort%5B%5D=sequence&sort%5B%5D=id&select%5B%5D=activities%3Aid%2Cuser_id%2Cclass_id%2Cadv_starred%2Cgroup_type%2Ctype%2Cpeer_assessment%2Cis_allow_repeat%2Ctitle%2Cdescription%2Cstart_date%2Cdue_date%2Cedit_group_mode%2Ccreated_at&select%5B%5D=user%3Aid%2Cfirstname_en%2Clastname_en%2Cfirstname_th%2Clastname_th&includes%5B%5D=user%3Asideload&includes%5B%5D=fileactivities%3Aids&includes%5B%5D=questions%3Aids"
    act_resp = session.get(activities_url, headers=headers)
    
    if act_resp.status_code == 200:
        data = act_resp.json()
        for act in data.get("activities", []):
            title = act.get("title")
            due = act.get("due_date")
            subject_name = class_mapping.get(cid, cid)
            
            # --- กรองงานที่ส่งแล้วออก ---
            submitted_at = act.get("activity_submission_submitted_at")
            quiz_submitted = act.get("quiz_submission_is_submitted")
            if submitted_at or quiz_submitted == 1:
                continue

            # ข้ามงานที่ไม่มีกำหนดส่ง
            if not due or "1970" in due:
                continue
                
            try:
                due_datetime = datetime.strptime(due, '%Y-%m-%d %H:%M:%S')
                due_datetime = bkk_tz.localize(due_datetime)
                
                # --- จัดการงานที่ Late ---
                is_exceed = act.get("due_date_exceed")
                status_prefix = ""
                
                # ถ้าเลยกำหนดแล้ว ให้แปะป้าย LATE และเลื่อนมาโชว์ในวันปัจจุบัน
                if now > due_datetime or is_exceed:
                    status_prefix = "[LATE] "
                    due_datetime = due_datetime.replace(year=now.year, month=now.month, day=now.day)

                # --- สร้าง Event ยัดใส่ Calendar ---
                e = Event()
                e.name = f"{status_prefix}[LEB2] {subject_name} - {title}"
                e.begin = due_datetime - timedelta(hours=1)
                e.end = due_datetime
                e.description = f"กำหนดส่งเดิม: {due}"
                
                cal.events.add(e)
                print(f"เพิ่มลง Calendar: {e.name}")
                
            except Exception as e:
                print(f"Error จัดการวันเวลาของงาน {title}: {e}")

# ==========================================
# Step 4: บันทึกไฟล์ .ics
# ==========================================
with open('leb2_homework.ics', 'w', encoding='utf-8') as f:
    f.write(cal.serialize())
    
print("\n[สำเร็จ] สร้างไฟล์ leb2_homework.ics เรียบร้อยแล้ว!")