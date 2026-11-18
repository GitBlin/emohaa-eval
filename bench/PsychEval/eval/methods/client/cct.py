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


class CCT(EvaluationMethod):

    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> dict[str, float]:
        """评估对话质量"""
        criteria_list = ["current focus", "non critical", "real connection", "self awareness", "self exploration"]
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
        
        for criteria in criteria_list:
            prompt = load_prompt("cct", criteria,"cn")
            
            template = Template(prompt)
            prompt = template.render(intake_form=profile, diag=dialogue)
            # print(f"CCT - {criteria} prompt: {prompt}")
            messages=[{"role": "user", "content": prompt}]     
            criteria_output = await self.chat_api(gpt_api, messages=messages, response_format=response_format)
            score = json.loads(criteria_output)
            print(f"CCT - {criteria} raw output:", score)
             # 解析 JSON
            # scores.extend(score)  报错
            # scores.extend(score['items'])
            scores.extend(score['items'])
        

        # outputs = dict(zip(criteria_list, scores))
        
        mean_score = 0
        
        if scores :
            for item in scores:
                print(f"item: {item}")
                mean_score += (item['score'] ) / 2 * 10 # 0-2 -> 0-10
                # print(f"item score: {item['score']}")
                # print(f"mean_score: {mean_score}")
            mean_score /= len(scores)
        else:
            mean_score = 0

        
        return {"client": mean_score}
    

    def get_name(self) -> str:
        return "CCT"