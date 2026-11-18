from typing import Any, Dict
import re

from openai import OpenAI

from manager.base import EvaluationMethod
from utils import load_prompt
from jinja2 import Template
import json

from typing import List
from pydantic import BaseModel, ConfigDict # 👈 确保导入 ConfigDict

class ItemScore(BaseModel):
    model_config = ConfigDict(extra='forbid')

    item: str
    score: float

class Items(BaseModel):                 # 用对象包一层
    model_config = ConfigDict(extra='forbid')
    items: List[ItemScore]


class PANAS(EvaluationMethod):

    def _parse_panas_response(self, data: list) -> float:
        """解析PANAS量表的响应"""
        # 首先，将列表转换为一个查找字典，方便快速获取分数
        # key是 'Interested', 'Excited' 等, value 是 2, 1 等
        data_lookup = {entry['item']: entry['score'] for entry in data}
        
        scores = {}
        
        # 您的原始情感列表（作为处理的基准）
        emotions = ['Interested', 'Excited', 'Strong', 'Enthusiastic', 'Proud', 'Alert', 'Inspired', 'Determined', 'Attentive', 'Active','Distressed', 'Upset', 'Guilty', 'Scared', 'Hostile', 'Irritable', 'Ashamed', 'Nervous', 'Jittery', 'Afraid']

        for emotion in emotions:
            # 从查找字典中获取原始分数
            original_score = data_lookup.get(emotion)
            
            if original_score is not None:
                # 关键：应用您完全相同的分数计算逻辑
                # (原始分数-1) * 2.5
                scores[f'panas_{emotion.lower()}'] = (original_score - 1) * 2.5


        # --- 从这里开始，下面的所有逻辑都与您的原始函数完全相同 ---
        
        # 计算正面情绪和负面情绪总分
        # (列表字段保持不变)
        
        
        positive_emotions = ['interested', 'excited', 'strong', 'enthusiastic', 'proud', 'alert', 'inspired', 'determined', 'attentive', 'active'] 
        negative_emotions = ['distressed', 'upset', 'guilty', 'scared', 'hostile', 'irritable', 'ashamed', 'nervous', 'jittery','afraid']
        
        positive_total = sum(scores.get(f'panas_{emotion}', 0) for emotion in positive_emotions)
        negative_total = sum(scores.get(f'panas_{emotion}', 0) for emotion in negative_emotions)
        
        final_scores = {}
        
        num_positive = len(positive_emotions)
        num_negative = len(negative_emotions)

        final_scores['positive'] = positive_total / num_positive if num_positive > 0 else 0
        final_scores['negative'] = negative_total / num_negative if num_negative > 0 else 0
        
        # (分数计算方式保持不变)
        final_score = (final_scores['positive'] - final_scores['negative'] + 10) / 2  # 转换为0-10分制
        
        return final_score

    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> dict[str, float]:
        """评估对话质量"""
        scores = []
        
        schema = Items.model_json_schema()
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "Items",
                "strict": True,
                "schema": schema
            }
        }
        
        prompt = load_prompt("panas", "panas","cn")
        
        template = Template(prompt)
        prompt = template.render(intake_form=profile, diag=dialogue)

        # print(f"panas - panas prompt: {prompt}")

        messages=[{"role": "user", "content": prompt}]     
        criteria_output = await self.chat_api(gpt_api, messages=messages, response_format=response_format)
        score = json.loads(criteria_output)
        print(f"panas - panas raw output:", score)
        # scores.extend(score['items'])
            # 解析 JSON

        # 3. 将您的数据（列表）转换为函数所需的字符串格式
        # 构建一个像 "Interested: 2\nExcited: 1\n..." 这样的字符串
        # score = {'items': [
        #     {'item': 'Interested', 'score': 2}, {'item': 'Excited', 'score': 1}, {'item': 'Strong', 'score': 3}, {'item': 'Enthusiastic', 'score': 2}, {'item': 'Proud', 'score': 3}, {'item': 'Alert', 'score': 2}, {'item': 'Inspired', 'score': 2}, {'item': 'Determined', 'score': 3}, {'item': 'Attentive', 'score': 3}, {'item': 'Active', 'score': 2}, 
        # {'item': 'Distressed', 'score': 4}, 
        # {'item': 'Upset', 'score': 4}, 
        # {'item': 'Guilty', 'score': 4}, 
        # {'item': 'Scared', 'score': 3}, 
        # {'item': 'Hostile', 'score': 2}, 
        # {'item': 'Irritable', 'score': 3}, 
        # {'item': 'Ashamed', 'score': 4}, 
        # {'item': 'Nervous', 'score': 4}, 
        # {'item': 'Jittery', 'score': 3}, 
        # {'item': 'Afraid', 'score': 4}]}
        final_score = self._parse_panas_response(score['items'])
        return {"client": final_score}


    def get_name(self) -> str:
        return "PANAS"