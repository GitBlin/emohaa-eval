import sys
import os

proxy_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]
for key in proxy_vars:
    # 如果环境变量存在，且值为空字符串，则删除它
    if key in os.environ and not os.environ[key]:
        del os.environ[key]
        print(f"[系统提示] 已自动清理无效的空环境变量: {key}")



sys.path.append(os.path.join(os.getcwd(), "eval"))



from collections import defaultdict
from typing import Dict, Any, DefaultDict, List, Tuple
from manager.base import EvaluationMethod
from utils.gpt5_chat_client import GPT5ChatClient
from methods import *
import json
import asyncio
import re
import glob
from pathlib import Path
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 填入API密钥和模型名称
# os.environ["CHAT_API_KEY"] = ""
# os.environ["CHAT_API_BASE"] = ""
# os.environ["CHAT_MODEL_NAME"] = ""



class ThreadSafeLogger:
    """线程安全的日志记录器，用于将所有print输出写入文件"""

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.terminal = sys.stdout  # 保存原始的终端输出
        self._lock = threading.Lock()  # 添加线程锁

        # 确保日志目录存在
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # 打开日志文件 - 使用二进制模式避免编码问题
        self.log_file = open(log_file_path, 'wb', buffering=0)

        # 写入开始时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_text = f"\n{'='*60}\n心理咨询对话评测系统 - 开始时间: {timestamp}\n{'='*60}\n\n"
        self.log_file.write(start_text.encode('utf-8', errors='ignore'))

    def write(self, text):
        """同时写入终端和日志文件 - 线程安全版本"""
        if not isinstance(text, str):
            text = str(text)

        # 写入终端（不需要锁）
        self.terminal.write(text)
        self.terminal.flush()

        # 写入日志文件 - 使用锁确保线程安全
        with self._lock:
            try:
                # 过滤掉可能导致问题的控制字符
                clean_text = text.replace('\x00', '').replace('\x08', '').replace('\x7f', '')
                self.log_file.write(clean_text.encode('utf-8', errors='ignore'))
            except Exception as e:
                # 如果写入失败，至少写入到终端
                self.terminal.write(f"\n[日志写入错误: {e}]\n")

    def flush(self):
        """刷新缓冲区"""
        self.terminal.flush()

    def close(self):
        """关闭日志文件"""
        with self._lock:
            if hasattr(self, 'log_file') and self.log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                end_text = f"\n{'='*60}\n心理咨询对话评测系统 - 结束时间: {timestamp}\n"

                try:
                    self.log_file.write(end_text.encode('utf-8', errors='ignore'))
                    self.log_file.close()
                except Exception as e:
                    self.terminal.write(f"\n[日志关闭错误: {e}]\n")

                # 恢复原始输出
                sys.stdout = self.terminal

    def get_thread_id(self):
        """获取当前线程ID用于日志标识"""
        return threading.current_thread().ident



class ThreadSafeFileWriter:
    """线程安全的文件写入器"""

    def __init__(self):
        self._locks = {}  # 文件路径到锁的映射
        self._master_lock = threading.Lock()  # 保护locks字典的锁

    def _get_file_lock(self, file_path: str) -> threading.Lock:
        """获取指定文件的锁"""
        with self._master_lock:
            if file_path not in self._locks:
                self._locks[file_path] = threading.Lock()
            return self._locks[file_path]

    def write_json(self, file_path: str, data: Dict[str, Any]) -> None:
        """线程安全的JSON文件写入"""
        file_lock = self._get_file_lock(file_path)
        with file_lock:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[文件写入错误] {file_path}: {e}")

    def append_to_file(self, file_path: str, text: str) -> None:
        """线程安全的文本追加写入"""
        file_lock = self._get_file_lock(file_path)
        with file_lock:
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(text)
            except Exception as e:
                print(f"[文件追加错误] {file_path}: {e}")


def load_data(file_path: str) -> Dict[str, Any]:
    """
    加载JSON数据文件

    Args:
        file_path: JSON文件路径

    Returns:
        解析后的JSON数据

    Raises:
        RuntimeError: 文件加载失败时抛出异常
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON data from {file_path}: {e}")


def load_profile_data(profile_path: str) -> Dict[str, Any]:
    """
    加载客户档案数据

    Args:
        profile_path: profile文件路径

    Returns:
        客户档案数据
    """
    return load_data(profile_path)


def load_session_data(session_path: str) -> List[Dict[str, Any]]:
    """
    加载会话对话数据

    Args:
        session_path: session文件路径

    Returns:
        会话对话数据列表
    """
    return load_data(session_path)


def extract_case_number(case_dir: str) -> str:
    """
    从case目录名提取编号

    Args:
        case_dir: case目录路径

    Returns:
        case编号字符串

    Raises:
        ValueError: 目录格式不正确时抛出异常
    """
    dir_name = os.path.basename(case_dir)
    # 从 "case-6_rep0" 格式中提取 "6"
    match = re.match(r"case-(\d+)_rep\d+", dir_name)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid case directory format: {dir_name}")


def find_all_case_representations(rft_root_dir: str) -> List[Tuple[str, str, str]]:
    """
    找到所有case的rep表示

    Args:
        rft_root_dir: RFT根目录路径

    Returns:
        (case_number, rep_name, case_path) 元组的列表

    Raises:
        RuntimeError: RFT目录不存在时抛出异常
    """
    all_cases = []

    if not os.path.isdir(rft_root_dir):
        raise RuntimeError(f"RFT directory '{rft_root_dir}' does not exist")

    # 遍历所有case目录
    for case_dir in os.listdir(rft_root_dir):
        case_path = os.path.join(rft_root_dir, case_dir)

        if os.path.isdir(case_path) and case_dir.startswith("case-"):
            case_number = extract_case_number(case_path)
            all_cases.append((case_number, case_dir, case_path))

    # 按case编号排序
    all_cases.sort(key=lambda x: int(x[0]))
    return all_cases


def find_specific_cases(rft_root_dir: str, target_cases: List[str]) -> List[Tuple[str, str, str]]:
    """
    找到指定的case列表

    Args:
        rft_root_dir: RFT根目录路径
        target_cases: 指定的case名称列表，如 ["case-5_rep0", "case-6_rep0"]

    Returns:
        (case_number, rep_name, case_path) 元组的列表
    """
    found_cases = []

    if not os.path.isdir(rft_root_dir):
        raise RuntimeError(f"RFT directory '{rft_root_dir}' does not exist")

    # 查找指定的case
    for case_name in target_cases:
        case_path = os.path.join(rft_root_dir, case_name)

        if os.path.isdir(case_path):
            case_number = extract_case_number(case_path)
            found_cases.append((case_number, case_name, case_path))
            print(f"找到目标case: {case_name}")
        else:
            print(f"警告: 目标case不存在: {case_name}")

    return found_cases


def find_json_files(sft_root_dir: str, target_files: List[str] = None) -> List[str]:
    """
    查找JSON文件

    Args:
        sft_root_dir: SFT根目录路径
        target_files: 指定的JSON文件列表，如果为None则查找所有JSON文件

    Returns:
        JSON文件路径列表
    """
    json_files = []

    if not os.path.isdir(sft_root_dir):
        raise RuntimeError(f"SFT directory '{sft_root_dir}' does not exist")

    if target_files:
        # 查找指定的JSON文件
        for target_file in target_files:
            if not target_file.endswith('.json'):
                target_file += '.json'
            file_path = os.path.join(sft_root_dir, target_file)
            if os.path.exists(file_path):
                json_files.append(file_path)
                print(f"找到目标文件: {target_file}")
            else:
                print(f"警告: 目标文件不存在: {target_file}")
    else:
        # 查找所有JSON文件
        for file in os.listdir(sft_root_dir):
            if file.endswith('.json'):
                json_files.append(os.path.join(sft_root_dir, file))

        # 按文件名排序
        json_files.sort()

    return json_files


class EvaluationManager:
    def __init__(self, max_workers: int = 4):
        self.methods: Dict[str, EvaluationMethod] = {}
        self._think_block_re = re.compile(r"<think>.*?</think>", flags=re.S)
        
        self.api_key = os.getenv("CHAT_API_KEY")  # 建议从环境变量或配置文件中加载密钥
        self.base_url = os.getenv("CHAT_API_BASE")  # 建议从环境变量或配置文件中加载密钥
        self.model_name = os.getenv("CHAT_MODEL_NAME")

        # 多线程相关配置
        self.max_workers = max_workers
        self.file_writer = ThreadSafeFileWriter()
        self._evaluation_lock = threading.Lock()  # 保护共享资源的锁
        self._stats_lock = threading.Lock()  # 保护统计信息的锁
        self._stats = {"completed": 0, "failed": 0, "in_progress": 0}  # 线程安全的统计信息

    def update_stats(self, key: str, increment: int = 1) -> None:
        """线程安全的统计信息更新"""
        with self._stats_lock:
            self._stats[key] += increment

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._stats_lock:
            return self._stats.copy()

    def process_single_file_thread(self, json_file_path: str, output_dir: str = None, thread_id: str = None) -> List[Dict[str, Any]]:
        """
        线程函数：处理单个JSON文件的所有session

        Args:
            json_file_path: JSON文件路径
            output_dir: 结果输出目录
            thread_id: 线程ID用于日志识别

        Returns:
            该文件的所有session评测结果
        """
        thread_name = threading.current_thread().name
        print(f"[线程 {thread_name}] 开始处理文件: {os.path.basename(json_file_path)}")

        self.update_stats("in_progress")
        case_results = []
        case_name = os.path.basename(json_file_path).replace('.json', '')

        try:
            # 加载JSON文件
            client_info, sessions = self.load_json_case(json_file_path)
            print(f"[线程 {thread_name}] 发现 {len(sessions)} 个session")

            # 对每个session做遍历
            for i, session_data in enumerate(sessions):
                session_number = session_data.get("session_number", i + 1)
                session_dialogue = self.extract_session_dialogue(session_data)

                print(f"[线程 {thread_name}] 处理Session {session_number}")

                try:
                    # 构建单个session的测试用例
                    test_case = self.build_test_case(client_info, session_dialogue)
                    print(f"[线程 {thread_name}] Session {session_number} 开始执行评测...")

                    # 在新的异步事件循环中执行评测
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        results = loop.run_until_complete(self.evaluate_single(test_case))
                        print(f"[线程 {thread_name}] Session {session_number} 评测完成")
                    finally:
                        loop.close()

                    # 创建结果对象
                    session_result = {
                        "case_name": case_name,
                        "case_number": client_info.get("client_id", ""),
                        "case_path": json_file_path,
                        "session_number": session_number,
                        "session_file": f"session_{session_number}",
                        "evaluation_results": results,
                        "session_count": 1,
                        "thread_id": thread_name
                    }

                    case_results.append(session_result)
                    print(f"[线程 {thread_name}] Session {session_number} 评测完成")

                    # 使用线程安全的文件写入器立即写入结果
                    if output_dir:
                        session_num = session_result["session_number"]
                        case_name_session = session_result["case_name"]
                        output_file = os.path.join(output_dir, f"{case_name_session}_session{session_num}.json")

                        self.file_writer.write_json(output_file, session_result)
                        print(f"[线程 {thread_name}] Session {session_number} 结果已保存到: {output_file}")

                except Exception as e:
                    import traceback
                    error_msg = f"Error evaluating session {session_number}: {e}\n"
                    error_msg += f"Traceback: {traceback.format_exc()}"
                    print(f"[线程 {thread_name}] Session {session_number} 评测失败: {e}")

                    # 创建错误结果对象
                    error_result = {
                        "case_name": case_name,
                        "case_number": client_info.get("client_id", ""),
                        "case_path": json_file_path,
                        "session_number": session_number,
                        "session_file": f"session_{session_number}",
                        "error": str(e),
                        "full_error": error_msg,
                        "evaluation_results": {},
                        "thread_id": thread_name
                    }

                    case_results.append(error_result)

                    # 使用线程安全的文件写入器写入错误结果
                    if output_dir:
                        session_num = error_result["session_number"]
                        case_name_session = error_result["case_name"]
                        output_file = os.path.join(output_dir, f"{case_name_session}_session{session_num}.json")

                        self.file_writer.write_json(output_file, error_result)
                        print(f"[线程 {thread_name}] Session {session_number} 错误结果已保存到: {output_file}")

            self.update_stats("completed")
            self.update_stats("in_progress", -1)
            print(f"[线程 {thread_name}] 文件处理完成: {case_name}")

        except Exception as e:
            self.update_stats("failed")
            self.update_stats("in_progress", -1)
            import traceback
            error_msg = f"Error processing JSON file {json_file_path}: {e}\n"
            error_msg += f"Traceback: {traceback.format_exc()}"
            print(f"[线程 {thread_name}] 处理文件 {case_name} 时发生错误: {e}")

            # 创建整个文件的错误结果
            error_result = {
                "case_name": case_name,
                "case_path": json_file_path,
                "error": str(e),
                "full_error": error_msg,
                "evaluation_results": {},
                "thread_id": thread_name
            }

            case_results.append(error_result)

        return case_results

    def load_json_case(self, json_file_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        加载单个JSON案例文件

        Args:
            json_file_path: JSON文件路径

        Returns:
            (client_info, sessions) 元组
        """
        try:
            data = load_data(json_file_path)
            client_info = data.get("client_info", {})
            sessions = data.get("sessions", [])
            return client_info, sessions
        except Exception as e:
            raise RuntimeError(f"Failed to load JSON case from {json_file_path}: {e}")

    def extract_session_dialogue(self, session_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从session对象中提取dialogue数据

        Args:
            session_data: session数据字典

        Returns:
            dialogue数据列表
        """
        return session_data.get("session_dialogue", [])

    def _remove_think_blocks(self, text: str) -> str:
        """隐藏<think>...</think>块"""
        
        text = text.replace("</end>", "")
        return self._think_block_re.sub("", text).strip()

    def process_session(self, session_dialogue: list[dict]) -> str:
        """
        将 session 对话转换为清晰的字符串格式：
        - user → client
        - assistant → counselor（并移除<think>块）
        """
        if not isinstance(session_dialogue, list):
            raise ValueError("session_dialogue 应该是一个列表")

        dialogue_lines = []
        for turn in session_dialogue:
            role = turn.get("role", "").strip().lower()
            content = turn.get("text", "").strip()

            if role == "system":
                continue
            elif role == "assistant" or role == "counselor":
                content = self._remove_think_blocks(content)
                dialogue_lines.append(f"counselor: {content}")
            elif role == "user" or role == "client":
                if re.match(r"^这是第\d+次会话$", content):
                    continue
                dialogue_lines.append(f"client: {content}")

        return "\n".join(dialogue_lines)

    def format_client_info(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将profile数据转换为评测所需的client_info格式

        Args:
            profile_data: 原始profile数据

        Returns:
            标准格式的client_info
        """
        client_info = {
            "static_traits": {
                "age": profile_data.get("static_traits", {}).get("age", ""),
                "name": profile_data.get("static_traits", {}).get("name", ""),
                "gender": profile_data.get("static_traits", {}).get("gender", ""),
                "occupation": profile_data.get("static_traits", {}).get("occupation", ""),
                "educational_background": profile_data.get("static_traits", {}).get("educational_background", ""),
                "marital_status": profile_data.get("static_traits", {}).get("marital_status", ""),
                "family_status": profile_data.get("static_traits", {}).get("family_status", ""),
                "social_status": profile_data.get("static_traits", {}).get("social_status", ""),
                "medical_history": profile_data.get("static_traits", {}).get("medical_history", ""),
                "language_features": profile_data.get("static_traits", {}).get("language_features", "")
            },
            "main_problem": profile_data.get("main_problem", ""),
            "topic": profile_data.get("topic", ""),
            "core_demands": profile_data.get("core_demands", ""),
            "growth_experience": profile_data.get("growth_experience", []),
            "core_brief": profile_data.get("core_brief", []),
            "special_situation": profile_data.get("special_situation", [])
        }

        return client_info

    def format_sessions_data(self, session_files: List[str]) -> List[Dict[str, Any]]:
        """
        格式化session数据为评测所需格式

        Args:
            session_files: session文件路径列表

        Returns:
            格式化的sessions数据
        """
        sessions = []

        for i, session_file in enumerate(session_files):
            try:
                session_data = load_session_data(session_file)
                session_number = i + 1

                session_info = {
                    "session_number": session_number,
                    "session_dialogue": session_data
                }

                sessions.append(session_info)

            except Exception as e:
                print(f"Warning: Failed to process session file {session_file}: {e}")
                continue

        return sessions

    def build_test_case(self, client_info: Dict[str, Any], session_dialogue: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建单个测试用例

        Args:
            client_info: 客户档案信息
            session_dialogue: 单个session的对话数据

        Returns:
            完整的测试用例数据

        Raises:
            RuntimeError: 数据加载失败时抛出异常
        """
        try:
            # 格式化client_info
            formatted_client_info = self.format_client_info(client_info)

            # 构建单个session
            session_info = {
                "session_number": 1,
                "session_dialogue": session_dialogue
            }

            return {
                "client_info": formatted_client_info,
                "sessions": [session_info]
            }

        except Exception as e:
            raise RuntimeError(f"Failed to build test case: {e}")


    def register(self, method: EvaluationMethod) -> None:
        """注册评估方法"""
        self.methods[method.get_name()] = method

    async def evaluate_single(self, case: Dict[str, Any]) -> Dict[str, list[Dict[str, float]]]:
        """
        对单个 case 执行所有注册的评估方法

        Args:
            case: 包含client_info和sessions的测试用例

        Returns:
            评测结果字典
        """
        profile = case.get("client_info")
        sessions = case.get("sessions")

        if not isinstance(sessions, list) or not sessions:
            raise ValueError("Invalid or missing sessions in case data.")

        # 合并所有session的对话数据
        all_dialogues = []
        for session in sessions:
            session_dialogue = session.get("session_dialogue", [])
            all_dialogues.extend(session_dialogue)

        if not all_dialogues:
            raise ValueError("No session dialogue found.")

        # 转换对话格式为字符串
        formatted_dialogue = self.process_session(all_dialogues)
        # print(formatted_dialogue)
        results: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
        
        async def run_evaluation(name, method):
            """运行单个评测方法"""
            print(f"[{threading.current_thread().name}] 开始评测方法: {name}")
            # 创建独立的GPT客户端，避免并发冲突
            gpt_api = GPT5ChatClient(api_key=self.api_key, base_url=self.base_url, model=self.model_name, rps=16)
            score = await method.evaluate(gpt_api, formatted_dialogue, profile)
            print(f"[{threading.current_thread().name}] 完成评测方法: {name}")
            return name, score

        # 并发执行所有评测方法
        tasks = [run_evaluation(name, method) for name, method in self.methods.items()]
        evaluations = await asyncio.gather(*tasks)

        print("Evaluations",evaluations)
        # 收集结果
        for name, score in evaluations:
            for key, value in score.items():
                print(f"Name:{name} - Key:{key}: Value{value}")
                results[key][name] = value

        return dict(results)

    async def evaluate_case(self, json_file_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """
        评测单个JSON文件，对每个session单独评测

        Args:
            json_file_path: JSON文件路径
            output_dir: 结果输出目录，如果提供则每个session处理完后立即写入文件

        Returns:
            包含每个session评测结果的列表
        """
        case_results = []
        case_name = os.path.basename(json_file_path).replace('.json', '')

        try:
            # 加载JSON文件
            client_info, sessions = self.load_json_case(json_file_path)
            print(f"  发现 {len(sessions)} 个session")


            # 对每个session做遍历
            for i, session_data in enumerate(sessions):
                session_number = session_data.get("session_number", i + 1)
                session_dialogue = self.extract_session_dialogue(session_data)

                print(f"  处理Session {session_number}")

                try:
                    # 构建单个session的测试用例
                    test_case = self.build_test_case(client_info, session_dialogue)

                    print("*******************")
                    # 执行评测
                    results = await self.evaluate_single(test_case)
                    print("-------------")
                    # 创建结果对象
                    session_result = {
                        "case_name": case_name,
                        "case_number": client_info.get("client_id", ""),
                        "case_path": json_file_path,
                        "session_number": session_number,
                        "session_file": f"session_{session_number}",
                        "evaluation_results": results,
                        "session_count": 1
                    }

                    # print(session_data)

                    case_results.append(session_result)
                    print(f"    Session {session_number} 评测完成")

                    # 立即写入单个session的结果文件
                    if output_dir:
                        session_num = session_result["session_number"]
                        case_name_session = session_result["case_name"]
                        # 生成便于区分的文件名：文件名_session编号.json
                        output_file = os.path.join(output_dir, f"{case_name_session}_session{session_num}.json")

                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(session_result, f, indent=2, ensure_ascii=False)
                        print(f"    Session {session_number} 结果已保存到: {output_file}")

                except Exception as e:
                    import traceback
                    error_msg = f"Error evaluating session {session_number}: {e}\n"
                    error_msg += f"Traceback: {traceback.format_exc()}"
                    print(f"    Session {session_number} 评测失败: {e}")

                    # 创建错误结果对象
                    error_result = {
                        "case_name": case_name,
                        "case_number": client_info.get("client_id", ""),
                        "case_path": json_file_path,
                        "session_number": session_number,
                        "session_file": f"session_{session_number}",
                        "error": str(e),
                        "full_error": error_msg,
                        "evaluation_results": {}
                    }

                    case_results.append(error_result)

                    # 立即写入错误结果文件
                    if output_dir:
                        session_num = error_result["session_number"]
                        case_name_session = error_result["case_name"]
                        # 生成便于区分的文件名：文件名_session编号.json
                        output_file = os.path.join(output_dir, f"{case_name_session}_session{session_num}.json")

                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(error_result, f, indent=2, ensure_ascii=False)
                        print(f"    Session {session_number} 错误结果已保存到: {output_file}")

        except Exception as e:
            import traceback
            error_msg = f"Error processing JSON file {json_file_path}: {e}\n"
            error_msg += f"Traceback: {traceback.format_exc()}"
            print(f"处理文件 {case_name} 时发生错误: {e}")

            # 创建整个文件的错误结果
            error_result = {
                "case_name": case_name,
                "case_path": json_file_path,
                "error": str(e),
                "full_error": error_msg,
                "evaluation_results": {}
            }

            case_results.append(error_result)

        return case_results

    async def process_all_cases(self, sft_root_dir: str, output_dir: str = None, specific_files: List[str] = None) -> List[Dict[str, Any]]:
        """
        批量处理JSON文件的评测

        Args:
            sft_root_dir: SFT根目录路径
            output_dir: 结果输出目录，如果为None则不保存文件
            specific_files: 指定的JSON文件列表，如果为None则处理所有JSON文件

        Returns:
            所有评测结果的列表
        """
        print(f"开始处理SFT数据，根目录: {sft_root_dir}")

        # 查找JSON文件
        json_files = find_json_files(sft_root_dir, specific_files)
        print(f"发现 {len(json_files)} 个JSON文件")

        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        all_results = []

        for i, json_file in enumerate(json_files, 1):
            file_name = os.path.basename(json_file)
            print(f"\n处理进度: {i}/{len(json_files)} - {file_name}")

            try:
                # 评测单个JSON文件的所有session
                session_results = await self.evaluate_case(json_file, output_dir)

                # 将session结果添加到总结果中
                all_results.extend(session_results)

                # 注意：每个session的结果已经在 evaluate_case 方法中立即写入了，不需要重复写入

                # 打印简要结果统计
                successful_sessions = [r for r in session_results if "evaluation_results" in r and r["evaluation_results"]]
                failed_sessions = [r for r in session_results if "error" in r]

                print(f"  Session评测统计: 成功 {len(successful_sessions)}, 失败 {len(failed_sessions)}")

            except Exception as e:
                print(f"处理 {file_name} 时发生错误: {e}")
                error_result = {
                    "case_name": file_name,
                    "case_path": json_file,
                    "error": str(e),
                    "evaluation_results": {}
                }
                all_results.append(error_result)

        # 保存汇总结果
        if output_dir and all_results:
            summary_file = os.path.join(output_dir, "evaluation_summary.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_files": len(json_files),
                    "successful_evaluations": len([r for r in all_results if "evaluation_results" in r and r["evaluation_results"]]),
                    "failed_evaluations": len([r for r in all_results if "error" in r]),
                    "results": all_results
                }, f, indent=2, ensure_ascii=False)
            print(f"\n汇总结果已保存到: {summary_file}")

        return all_results

    async def process_all_cases_multithreaded(self, sft_root_dir: str, output_dir: str = None, specific_files: List[str] = None) -> List[Dict[str, Any]]:
        """
        多线程批量处理JSON文件的评测

        Args:
            sft_root_dir: SFT根目录路径
            output_dir: 结果输出目录，如果为None则不保存文件
            specific_files: 指定的JSON文件列表，如果为None则处理所有JSON文件

        Returns:
            所有评测结果的列表
        """
        print(f"[主线程] 开始多线程处理SFT数据，根目录: {sft_root_dir}")
        print(f"[主线程] 最大线程数: {self.max_workers}")

        # 查找JSON文件
        json_files = find_json_files(sft_root_dir, specific_files)
        print(f"[主线程] 发现 {len(json_files)} 个JSON文件")

        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        all_results = []

        # 使用线程池执行多线程处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.process_single_file_thread, json_file, output_dir, f"thread_{i}"): json_file
                for i, json_file in enumerate(json_files)
            }

            # 收集结果
            for future in as_completed(future_to_file):
                json_file = future_to_file[future]
                try:
                    file_results = future.result()
                    all_results.extend(file_results)

                    # 打印进度和统计信息
                    stats = self.get_stats()
                    print(f"[主线程] 文件完成: {os.path.basename(json_file)} | 统计: 完成={stats['completed']}, 失败={stats['failed']}, 处理中={stats['in_progress']}")

                except Exception as e:
                    print(f"[主线程] 处理文件 {os.path.basename(json_file)} 时发生异常: {e}")
                    error_result = {
                        "case_name": os.path.basename(json_file),
                        "case_path": json_file,
                        "error": str(e),
                        "evaluation_results": {}
                    }
                    all_results.append(error_result)

        # 保存汇总结果
        if output_dir and all_results:
            summary_file = os.path.join(output_dir, "evaluation_summary_multithreaded.json")
            final_stats = self.get_stats()
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_files": len(json_files),
                    "max_workers": self.max_workers,
                    "successful_evaluations": len([r for r in all_results if "evaluation_results" in r and r["evaluation_results"]]),
                    "failed_evaluations": len([r for r in all_results if "error" in r]),
                    "stats": final_stats,
                    "results": all_results
                }, f, indent=2, ensure_ascii=False)
            print(f"[主线程] 汇总结果已保存到: {summary_file}")

        return all_results

    def generate_detailed_report(self, results: List[Dict[str, Any]], output_dir: str) -> None:
        """
        生成详细的评测报告
        Args:
            results: 评测结果列表
            output_dir: 输出目录
        """
        report_file = os.path.join(output_dir, "detailed_report.txt")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("心理咨询对话评测详细报告\n")
            f.write("=" * 50 + "\n\n")

            # 统计信息
            successful = [r for r in results if "evaluation_results" in r and r["evaluation_results"]]
            failed = [r for r in results if "error" in r]

            f.write(f"总体统计:\n")
            f.write(f"  总处理数量: {len(results)}\n")
            f.write(f"  成功评测: {len(successful)}\n")
            f.write(f"  失败评测: {len(failed)}\n\n")

            # 成功案例的详细结果
            if successful:
                f.write("成功评测案例详情:\n")
                f.write("-" * 30 + "\n")

                for result in successful:
                    f.write(f"\n案例: {result['case_name']}\n")
                    f.write(f"Session数量: {result.get('session_count', 'N/A')}\n")

                    if "evaluation_results" in result and result["evaluation_results"]:
                        for dimension, methods in result["evaluation_results"].items():
                            f.write(f"  {dimension}:\n")
                            for method_name, score in methods.items():
                                f.write(f"    {method_name}: {score}\n")
                    f.write("\n")

            # 失败案例
            if failed:
                f.write("\n失败评测案例:\n")
                f.write("-" * 30 + "\n")

                for result in failed:
                    f.write(f"\n案例: {result['case_name']}\n")
                    f.write(f"错误: {result.get('error', 'Unknown error')}\n")

        print(f"详细报告已保存到: {report_file}")


async def main():
    """
    主程序入口 - 多线程版本
    """
    # 设置日志文件路径
    # log_file_path = "eval/results/Simpsydial/logger.txt"
    log_file_path = "eval/results/PsychEval_results/cbt/logger.txt"
    # 设置目录路径
    # sft_root_dir =  "eval/manager/Simpsydial/prepared"
    sft_root_dir =  "eval/data_sample/PsychEval/cbt"
    # output_dir =    "eval/results/Simpsydial"
    output_dir =    "eval/results/PsychEval_results/cbt"

    print(f"\n配置信息:")
    print(f"  SFT数据目录: {sft_root_dir}")
    print(f"  结果输出目录: {output_dir}")
    print(f"  日志文件: {log_file_path}")

    # 启动线程安全的日志记录
    logger = ThreadSafeLogger(log_file_path)
    sys.stdout = logger

    try:
        eval_manager = EvaluationManager(max_workers=15)

        # evaluation methods registration
        print("注册评测方法...")
        # for method_cls in [ HTAIS, RRO, WAI, Custom_Dim, PANAS, SCL_90, SRS ]:
        for method_cls in [ HTAIS, RRO, WAI, Custom_Dim,CTRS, PANAS, SCL_90, SRS,BDI_II ]:
            method_instance = method_cls()
            eval_manager.register(method_instance)
            print(f"  已注册: {method_instance.get_name()}")

        results = await eval_manager.process_all_cases_multithreaded(
            sft_root_dir=sft_root_dir,
            output_dir=output_dir
        )

        print(f"\n=== 评测完成统计 ===")
        successful = len([r for r in results if "evaluation_results" in r and r["evaluation_results"]])
        failed = len([r for r in results if "error" in r])
        print(f"总处理数量: {len(results)}")
        print(f"成功评测: {successful}")
        print(f"失败评测: {failed}")

        if successful > 0:
            print(f"\n评测方法统计:")
            method_stats = defaultdict(int)
            for result in results:
                if "evaluation_results" in result and result["evaluation_results"]:
                    for method_name in result["evaluation_results"].get("counselor", {}):
                        method_stats[method_name] += 1

            for method, count in method_stats.items():
                print(f"  {method}: {count} 次")

            eval_manager.generate_detailed_report(results, output_dir)

        print(f"\n所有输出已保存到日志文件: {log_file_path}")

    except Exception as e:
        print(f"主程序执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.close()


if __name__ == '__main__':
    asyncio.run(main())
