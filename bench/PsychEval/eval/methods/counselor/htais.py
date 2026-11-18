from typing import Any, Dict
import json
from openai import OpenAI
from pydantic import BaseModel, ConfigDict # 👈 确保导入 ConfigDict
from manager.base import EvaluationMethod
from utils import load_prompt
from typing import List
from pydantic import BaseModel
from jinja2 import Template

class ItemScore(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item: str
    score: float
    # reason: str

class Items(BaseModel):                 # 用对象包一层
    model_config = ConfigDict(extra='forbid')
    items: List[ItemScore]



class HTAIS(EvaluationMethod):

    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> Dict[str, Any]:

        # 读取 prompt，并替换 {diag} 占位符
        prompt = load_prompt("HTAIS", "HTAIS","cn")

        template = Template(prompt)

        prompt = template.render(intake_form=profile, diag=dialogue)

        # print(f"HTAIS - HTAIS prompt: {prompt}")
        # 结合 intake_form 分析
        # intake_form_str = json.dumps(profile, ensure_ascii=False)
        # prompt = prompt_template.replace("{diag}", dialogue).replace("{intake_form}", intake_form_str)
        
        messages=[{"role": "user", "content": prompt}]

        schema = Items.model_json_schema()
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "Items",
                "strict": True,
                "schema": schema
            }
        }

        # 调用 GPT 接口
        criteria_output = await self.chat_api(gpt_api, messages=messages, response_format=response_format)
        print("HTAIS raw output:", criteria_output)
         # 解析 JSON
        score = json.loads(criteria_output)
        scores= []
        scores.extend(score['items'])
        
        mean_score = 0
        
        # 把只有一个prompt的多项目当作多个prompt的多项目处理
        for item in scores:
            print(f"item: {item}")
            mean_score += (item['score']-1) * 2.5 # 1-5 -> 0-10

        mean_score /= len(scores)
        
        return {"counselor": mean_score}

    def get_name(self) -> str:
        return "HTAIS"
