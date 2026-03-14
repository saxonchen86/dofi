import datetime
import logging

logger = logging.getLogger("dofi_skills")

def convert_time(timestamp_input: str | int | float, tz_offset: int = 8) -> str:
    """
    工业级时间戳转换器，自适应秒/毫秒级时间戳。
    """
    try:
        ts = float(str(timestamp_input).strip())
        
        # 启发式判断：自适应毫秒与秒
        if ts > 1e11: 
            ts /= 1000.0
            
        tz = datetime.timezone(datetime.timedelta(hours=tz_offset))
        dt = datetime.datetime.fromtimestamp(ts, tz=tz)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
        
    except ValueError:
        logger.error(f"非法的时间戳输入: {timestamp_input}")
        return f"Error: 无法将 '{timestamp_input}' 解析为有效时间戳"
    except Exception as e:
        logger.error(f"转换时间戳时发生未知错误: {e}")
        return f"Error: 系统内部异常 {str(e)}"
