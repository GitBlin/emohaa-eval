from pathlib import Path

def get_project_dir(dir_name="eval"):
    """
    从当前文件向上寻找，直到找到包含目标文件夹的路径
    """
    current_path = Path(__file__).resolve()
    
    for parent in current_path.parents:
        # 如果当前父目录下有名为 eval 的子目录，则认定为项目根级目录
        if (parent / dir_name).is_dir():
            return parent / dir_name
    
    # 如果没找到，默认返回当前文件的上两级（即 eval 目录）
    return current_path.parent.parent

# 自动获取 eval 目录的绝对路径
EVAL_ROOT = get_project_dir("eval")

# 定位到 results 目录
RESULTS_DIR = EVAL_ROOT / "results"
# 确保目录存在（如果不存在则创建）
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def load_prompt(method_name, prompt_name, language="cn"):
    # 使用 / 符号直接拼接路径，非常直观
    prompt_path = EVAL_ROOT / f"prompts_{language}" / method_name / f"{prompt_name}.txt"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()