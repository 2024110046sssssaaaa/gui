import re
import time
import subprocess
from appium.webdriver.common.appiumby import AppiumBy


def extract_numbers(input_string):
    return re.sub(r"\D", "", input_string)


def call(port=5554, driver=None, number=""):
    number = extract_numbers(number)
    command = f"adb -s emulator-{port} shell am start -a android.intent.action.CALL -d tel:{number}"
    _ = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if number == "911":
        while True:
            try:
                call_UI = driver.find_element(AppiumBy.XPATH, '//android.widget.Button[@content-desc="dial"]')
                call_UI.click()
                break
            except:
                time.sleep(0.5)
    return number
    

def check_call_number(driver):
    if driver.current_activity == "com.android.dialer.incall.activity.ui.InCallActivity":
        try:
            number_UI = driver.find_element(
                AppiumBy.ID, "com.google.android.dialer:id/contactgrid_contact_name")
            number = number_UI.text.replace('\u202a', '').replace('\u202c', '')
            return number
        except:
            return "special_call"
    else:
     	return "None"
  
  
def is_calling(port=5554):
    command = f'adb -s emulator-{port} shell dumpsys telephony.registry | grep "mCallState"'
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "mCallState=2" in result.stdout.decode("utf-8"):
        return True
    else:
        return False


def get_recent_calls(port=5554, num=10):
    """
    获取近期通话记录
    Args:
        port: adb 端口
        num: 获取记录数量
    Returns:
        list: 通话记录列表，每个记录为 dict 包含 number, type(来电/去电), date
    """
    try:
        # 查询通话记录数据库
        command = f"adb -s emulator-{port} shell"
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
        )
        # 使用 content query 查询通话记录
        process.stdin.write("su\n")
        process.stdin.flush()
        query = f"content query --uri content://call_log/calls --projection number,type,date --limit {num}\n"
        process.stdin.write(query)
        process.stdin.flush()
        stdout, _ = process.communicate(timeout=10)

        calls = []
        lines = stdout.strip().split("\n")
        for line in lines:
            # 解析每一行通话记录
            # 格式类似: Row: number=1234567890, type=2, date=1234567890
            if "number=" in line:
                parts = line.split(", ")
                call_info = {}
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        call_info[key.strip()] = value.strip()
                if call_info.get("number"):
                    calls.append({
                        "number": call_info.get("number", ""),
                        "type": "outgoing" if call_info.get("type") == "2" else "incoming",
                        "date": call_info.get("date", "")
                    })
        return calls
    except Exception as e:
        # 如果 content query 失败，尝试使用 dumpsys
        try:
            command = f"adb -s emulator-{port} shell dumpsys telecom"
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # 简单的解析，实际可能需要更复杂的逻辑
            return []
        except:
            return []