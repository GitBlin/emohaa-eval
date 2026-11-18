from typing import Any, Dict
import re

from openai import OpenAI

from manager.base import EvaluationMethod
from utils import load_prompt
from jinja2 import Template

from typing import List
from pydantic import BaseModel, ConfigDict # 👈 确保导入 ConfigDict
import json

class ItemScore(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item: str
    score: float

class Items(BaseModel):                 # 用对象包一层
    model_config = ConfigDict(extra='forbid')
    items: List[ItemScore]


class CTRS(EvaluationMethod):
    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> Dict[str, float]:
        criteria_list = ["understanding", "interpersonal_effectiveness", "collaboration", "guided_discovery", "focus",
                         "strategy"]
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

            # 用temple方法替换
            prompt = load_prompt("ctrs", criteria,"cn")

            template = Template(prompt)
            # prompt中要替换的变量
            prompt = template.render(diag=dialogue)

            messages=[{"role": "user", "content": prompt}]
            
            # print(f"ctrs - {criteria} prompt: {prompt}")
            # 返回{"items": [ {"item": "...", "score": ...}, ... ]}
            criteria_output = await self.chat_api(gpt_api, messages=messages,response_format=response_format)

            score = json.loads(criteria_output)

            # print(f"ctrs - {criteria} raw output: {score}")   
            
            # score = score / 6 * 10 # Convert to a 0-10 scale
            print(f"Criteria: {criteria}, Score: {score}")
            scores.extend(score['items'])

        mean_score = 0
        
        if scores :
            for item in scores:
                print(f"item: {item}")
                mean_score += (item['score'] ) / 6 * 10 # 0-6 -> 0-10
                # print(f"item score: {item['score']}")
                # print(f"mean_score: {mean_score}")
            mean_score /= len(scores)
        else:
            mean_score = 0

        print(f"CTRS mean_score: {mean_score}")
        return {"counselor": mean_score}
    
    
    def get_name(self) -> str:
        return "CTRS"