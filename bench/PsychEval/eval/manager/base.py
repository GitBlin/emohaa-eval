from abc import ABC, abstractmethod
from typing import Dict, Any


class EvaluationMethod(ABC):
    
    async def chat_api(self, gpt_api, messages, response_format=None) -> Dict[str, float]:
        
        res = await gpt_api.chat_text(messages=messages, response_format=response_format)
        
        return res
    
    async def evaluate(self, gpt_api, dialogue: Any, profile: dict = None) -> Dict[str, float]:
        pass

    def get_name(self) -> str:
        """返回类名称

        调用被子类继承的方法时，返回子类的类名
        """
        return self.__class__.__name__
