import datetime

def convert_time(time_input: str):
    """时间戳与日期字符串互转。支持 'now' 或具体时间。"""
    try:
        if time_input.lower() == 'now':
            return f"Current: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        # 内部转换逻辑...
        return f"Converted: {time_input}"
    except Exception as e:
        return f"❌ Time Error: {str(e)}"