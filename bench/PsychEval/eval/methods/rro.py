from typing import Any, Dict, List, Set
import json
from openai import OpenAI  # 假设这个是你的 chat_api 客户端

from manager.base import EvaluationMethod
from utils import load_prompt
# from typing import List # 这一行是重复导入
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from jinja2 import Template

# --- Pydantic 模型定义 ---

class ItemScore(BaseModel):
    """用于最终报告的条目评分结构"""
    model_config = ConfigDict(extra='forbid')

    item: int = Field(ge=1, le=24, description="项目编号 (整数)")
    # --- 修正 1: 验证范围必须是 0-10 ---
    score: float = Field(ge=0, le=10, description="项目得分 (0-10)")

class FactorScores(BaseModel):
    """四个因子的得分结构"""
    model_config = ConfigDict(extra='forbid')

    # --- 修正 2: 所有因子的验证范围都必须是 0-10 ---
    client_realism: float = Field(alias="Client Realism", ge=0, le=10)
    client_genuineness: float = Field(alias="Client Genuineness", ge=0, le=10)
    counselor_realism: float = Field(alias="counselor Realism", ge=0, le=10)
    counselor_genuineness: float = Field(alias="counselor Genuineness", ge=0, le=10)

class Report(BaseModel):
    """最终评估报告的完整结构"""
    model_config = ConfigDict(extra='forbid')
    
    items: List[ItemScore]
    factor_scores: FactorScores


# --- 为 LLM JSON 模式新增的模型 ---

class LLMItem(BaseModel):
    """定义 LLM 输出的条目格式"""
    item: str = Field(description="评估项目列表中的编号的字符串形式 (例如 '1', '2')")
    score: int = Field(ge=1, le=5, description="1到5分的原始评分")

class LLMResponse(BaseModel):
    """定义 LLM 响应的根 JSON 对象"""
    items: List[LLMItem] = Field(description="包含所有24个项目评分的列表")


# --- 评估方法实现 ---

class RRO(EvaluationMethod):

    # --- 因子计算的常量 ---
    REVERSE_SCORED_ITEMS: Set[int] = {2, 7, 16, 17, 18, 19, 24}
    
    FACTOR_DEFINITIONS: Dict[str, List[int]] = {
        # 键名必须与 FactorScores Pydantic 模型的别名(alias)匹配
        "Client Realism": [1, 8, 9, 10, 12, 20, 17, 16, 22],
        "Client Genuineness": [4, 11, 18, 24],
        "counselor Realism": [2, 6, 15, 21, 23, 19],
        "counselor Genuineness": [3, 5, 7, 13, 14]
    }
    
    def _calculate_factor_avg(self, 
                             item_numbers: List[int], 
                             scores_map: Dict[int, float], 
                             reverse_set: Set[int]) -> float:
        """
        辅助函数：计算单个因子的平均分，处理反向计分
        """
        total = 0.0
        count = 0
        for item_num in item_numbers:
            if item_num in scores_map:
                score = scores_map[item_num] # score 已经是 0-10 的 float
                if item_num in reverse_set:
                    total += (10.0 - score) # 反向计分 (0-10 范围)
                else:
                    total += score
                count += 1
            else:
                # 这是一个严重错误，意味着LLM的输出不完整
                print(f"警告: 在计算因子时未找到项目 {item_num} 的分数。")
        
        return total / count if count > 0 else 0.0


    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> Dict[str, Any]:
        """
        对话评估函数，返回24个条目的分数以及计算后的因子分数。
        """
        
        # --- 修正 3: 移除了您粘贴的重复且已注释掉的旧 evaluate 函数代码 ---
        
        # 1. 使用 LLMResponse (匹配Prompt) 来生成 Schema
        schema = LLMResponse.model_json_schema()

        response_format={
            "type": "json_schema",
            "json_schema": {  
                "name": "ScoringReport",  
                "strict": True,  
                "schema": schema  
            }
        }

        # 2. 加载和渲染 Prompt
        prompt = load_prompt("RRO", "RRO", "cn") # 假设 load_prompt 能找到你提供的Prompt
        template = Template(prompt)
        prompt_content = template.render(intake_form=profile, diag=dialogue)

        # print(f"RRO - RRO prompt: {prompt_content}...") 

        messages=[{"role": "user", "content": prompt_content}]
        
        # 3. 调用 GPT 接口
        try:
            criteria_output = await self.chat_api(gpt_api, messages=messages, response_format=response_format)
            # 4. 解析 JSON
            score_data = json.loads(criteria_output)
            
            # 验证LLM的输出是否符合 LLMResponse 规范
            llm_response = LLMResponse.model_validate(score_data)
            llm_items = llm_response.items

        except json.JSONDecodeError as e:
            print(f"RRO - RRO 严重错误: LLM 输出不是有效的 JSON. 错误: {e}")
            print(f"RRO - RRO 原始输出: {criteria_output}")
            return {"error": "LLM_JSON_DECODE_ERROR", "raw_output": criteria_output}
        except ValidationError as e:
            print(f"RRO - RRO 严重错误: LLM 输出不符合 Schema. 错误: {e}")
            print(f"RRO - RRO 原始数据: {score_data}")
            return {"error": "LLM_SCHEMA_VALIDATION_ERROR", "data": score_data}
        except Exception as e:
            print(f"RRO - RRO 严重错误: API 调用失败. 错误: {e}")
            return {"error": f"API_CALL_FAILED: {e}"}

        print(f"RRO - RRO raw output parsed: {llm_items}")

        # 5. --- 核心计算逻辑 ---
        
        item_scores_map: Dict[int, float] = {}
        parsed_items_for_report: List[ItemScore] = [] # 这个列表现在不会在最终返回，但保留它用于调试或未来扩展

        # 转换数据：从LLM格式转为Report格式，并构建用于计算的Map
        for item_dict in llm_items:
            try:
                item_num_int = int(item_dict.item)
                score_int_1_5 = int(item_dict.score) # 这是 1-5 的原始分数
                
                # --- START: 应用您的转换公式 ---
                score_float_0_10 = (score_int_1_5 - 1) * 2.5
                # --- END: 应用您的转换公式 ---
                
                # a) 添加到 Map 用于因子计算
                item_scores_map[item_num_int] = score_float_0_10
                
                # b) 创建 ItemScore 对象 (您已成功移除 reason)
                parsed_items_for_report.append(
                    ItemScore(item=item_num_int, score=score_float_0_10)
                )
            except (ValueError, TypeError) as e:
                print(f"RRO - RRO 错误: 解析LLM条目时出错: {item_dict}. 错误: {e}")
                continue
        
        if len(item_scores_map) != 24:
             print(f"RRO - RRO 警告: 预期 24 个评分项, 但只成功解析了 {len(item_scores_map)} 项。")


        # 6. 计算所有因子分数
        calculated_factor_scores: Dict[str, float] = {}
        for factor_name, item_list in self.FACTOR_DEFINITIONS.items():
            avg_score = self._calculate_factor_avg(
                item_list, 
                item_scores_map, 
                self.REVERSE_SCORED_ITEMS
            )
            calculated_factor_scores[factor_name] = avg_score

        print(f"RRO - RRO Calculated factors: {calculated_factor_scores}")

        # 7. 构建并验证最终的返回对象
        try:
            validated_factor_scores = FactorScores.model_validate(calculated_factor_scores)
            
            # --- START: 按照用户要求修改返回结构 ---
            
            client_avg = (validated_factor_scores.client_realism + validated_factor_scores.client_genuineness) / 2.0
            counselor_avg = (validated_factor_scores.counselor_realism + validated_factor_scores.counselor_genuineness) / 2.0
            
            final_scores = {
                "client": client_avg,
                "counselor": counselor_avg
            }
            
            print(f"RRO - RRO Final aggregated scores: {final_scores}")
            
            # --- END: 按照用户要求修改返回结构 ---

        except ValidationError as e:
            print(f"RRO - RRO 严重错误: 最终报告Pydantic验证失败. 错误: {e}")
            print(f"RRO - RRO 因子数据: {calculated_factor_scores}")
            return {"error": "FINAL_REPORT_VALIDATION_ERROR", "data": str(e)}

        # 8. 返回结构
        return final_scores

    def get_name(self) -> str:
        return "RRO"