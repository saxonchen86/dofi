import urllib.request
import urllib.error
import socket
import json

def check_milvus_health(host="milvus-standalone", http_port=9091, rpc_port=19530):
    """
    深度诊断 Milvus 的运行状态，返回结构化诊断报告
    """
    report = {
        "target_host": host,
        "http_health_check": "FAILED",
        "rpc_port_status": "CLOSED",
        "overall_readiness": False,
        "diagnostic_msg": ""
    }

    # 1. 检查 RPC 端口 (19530)
    # 如果 RPC 端口没通，说明 gRPC Server 根本没起来
    try:
        with socket.create_connection((host, rpc_port), timeout=3):
            report["rpc_port_status"] = "OPEN"
    except (socket.timeout, socket.error):
        report["diagnostic_msg"] += f"[RPC] 端口 {rpc_port} 拒绝连接。Milvus 主进程可能崩溃或仍在初始化。"

    # 2. 检查 HTTP 探活端点 (9091/healthz)
    # 即使端口通了，应用层可能还在等待 etcd/minio
    health_url = f"http://{host}:{http_port}/healthz"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            
            if status_code == 200:
                report["http_health_check"] = "OK"
                # Milvus 的 healthz 通常返回 "OK"
                if "OK" in body.upper():
                    report["overall_readiness"] = True
                    report["diagnostic_msg"] = "Milvus 所有组件已就绪，RPC 通道已开启，可正常接受请求。"
            else:
                report["diagnostic_msg"] += f" [HTTP] 探活返回异常状态码: {status_code}。"
                
    except urllib.error.URLError as e:
        report["diagnostic_msg"] += f" [HTTP] 无法访问探活接口 ({e.reason})。可能是 etcd 或 minio 挂载失败导致死锁。"
    except Exception as e:
        report["diagnostic_msg"] += f" [HTTP] 发生未知错误: {str(e)}"

    # 综合判定
    if report["rpc_port_status"] == "OPEN" and not report["overall_readiness"]:
        report["diagnostic_msg"] += " 注意：RPC 端口已开启，但内部组件未 Ready (假死状态)，请检查容器日志中的依赖项状态。"

    return json.dumps(report, ensure_ascii=False, indent=2)

# 供 Dofi 调用的入口
if __name__ == "__main__":
    # Dofi 可以通过解析传入的 arguments 来覆盖默认值
    # 这里直接执行默认检查作为演示
    print(check_milvus_health())