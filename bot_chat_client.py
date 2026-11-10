#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体开放平台客户端调用脚本 (已配置测试环境「高中小学校」默认凭证)

核心功能：
  1. POST /psychology-api/apis/auth             - 生成/换取用户令牌 (apiKey + apiSecret + userId)
  2. GET  /psychology-api/open/bot/list         - 获取当前机构可用智能体列表
  3. POST /psychology-api/open/chat/completions    - 发送消息/问候语 (自适应支持 SSE 流式与 JSON 解析)

支持操作：
  - 打印智能体列表:   python3 bot_chat_client.py --list
  - 遍历发送问候语:   python3 bot_chat_client.py --greet-all --msg "你好！很高兴认识你。"
  - 单独向智能体发送: python3 bot_chat_client.py --send --bot-id 265 --msg "你能介绍一下你自己吗？"
"""

import sys
import json
import argparse
import requests
import urllib3

# 关闭自签名证书告警
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 测试环境「高中小学校」(OrgId: 440) 默认配置
DEFAULT_BASE_URL = "https://www.ai-role.cn"
DEFAULT_API_KEY = "psy_0833aef583de4f"
DEFAULT_API_SECRET = "ee8690039995479da09f1f5411211083"
DEFAULT_USER_ID = "test_user_demo_01"


class BotChatClient:
    def __init__(self, api_key: str = DEFAULT_API_KEY, api_secret: str = DEFAULT_API_SECRET, base_url: str = DEFAULT_BASE_URL):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.access_token = None
        self.session = requests.Session()
        self.session.trust_env = False

    def auth_user(self, user_id: str = DEFAULT_USER_ID) -> str:
        """
        1. 使用 apiKey + apiSecret + userId 获取访问令牌。
        若平台不存在该 userId 对应用户，服务端会自动创建并注册该用户。
        """
        url = f"{self.base_url}/psychology-api/apis/auth"
        payload = {
            "apiKey": self.api_key,
            "apiSecret": self.api_secret,
            "userId": str(user_id)
        }
        resp = self.session.post(url, json=payload, timeout=10, verify=False)
        resp.raise_for_status()
        data = resp.json()
        
        token = (data.get("data") or {}).get("access_token")
        if not token:
            raise RuntimeError(f"用户认证失败: {data.get('message', data)}")
        
        self.access_token = token
        return self.access_token

    def _get_headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("尚未获取 access_token，请先调用 auth_user(user_id) 进行认证！")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_bot_list(self) -> list:
        """
        2. 获取当前机构下该用户可访问的全部智能体列表。
        """
        url = f"{self.base_url}/psychology-api/open/bot/list"
        resp = self.session.get(url, headers=self._get_headers(), timeout=10, verify=False)
        resp.raise_for_status()
        res = resp.json()
        if not res.get("success"):
            raise RuntimeError(f"获取智能体列表失败: {res.get('message')}")
        return res.get("data") or []

    def _parse_reply(self, resp: requests.Response) -> str:
        """
        自适应解析智能体回复：
        由于部分智能体底层配置为流式输出 (text/event-stream)，部分为 JSON (application/json)，
        本函数自适应兼顾两种协议，彻底杜绝 JSONDecodeError。
        """
        ctype = resp.headers.get("content-type", "").lower()
        if "text/event-stream" in ctype:
            full_text = []
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str in ("[DONE]", ""):
                        continue
                    try:
                        obj = json.loads(data_str)
                        choices = obj.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content") or ""
                            full_text.append(content)
                    except Exception:
                        pass
            return "".join(full_text).strip()
        else:
            res = resp.json()
            return (res.get("data") or {}).get("content", "").strip() or res.get("message", "")

    def send_message(self, bot_id: int, content: str = "你好！") -> str:
        """
        3. 向指定智能体发送单条消息，获取智能体回复。
        """
        url = f"{self.base_url}/psychology-api/open/chat/completions"
        payload = {
            "botId": bot_id,
            "content": content,
            "isStream": True
        }
        resp = self.session.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=30,
            verify=False,
            stream=True
        )
        resp.raise_for_status()
        return self._parse_reply(resp)

    def greet_all_bots(self, greeting_text: str = "你好！很高兴认识你。", limit: int = None):
        """
        4. 遍历所有智能体逐一发送问候语。
        """
        bots = self.get_bot_list()
        target_bots = bots[:limit] if limit else bots
        print(f"\n[INFO] 共获取到 {len(bots)} 个智能体，本次测试发送 {len(target_bots)} 个：\n")
        
        results = []
        for i, bot in enumerate(target_bots, 1):
            bid = bot.get("id")
            bname = bot.get("name", "未命名智能体")
            pos = bot.get("position", "无定位")
            print(f"[{i}/{len(target_bots)}] 发送至 【{bname}】(ID: {bid} | 定位: {pos})")
            print(f"  ├─ 发送消息: '{greeting_text}'")
            try:
                reply = self.send_message(bid, greeting_text)
                print(f"  └─ 智能体回复: {reply if reply else '(空回复)'}\n")
                results.append({"bot_id": bid, "name": bname, "status": "成功", "reply": reply})
            except Exception as e:
                print(f"  └─ 发送失败: {e}\n")
                results.append({"bot_id": bid, "name": bname, "status": "失败", "error": str(e)})
        return results


def main():
    parser = argparse.ArgumentParser(description="智能体开放接口交互脚本 (带测试环境默认配置)")
    parser.add_argument("--key", dest="api_key", help="应用的 API Key", default=DEFAULT_API_KEY)
    parser.add_argument("--secret", dest="api_secret", help="应用的 API Secret", default=DEFAULT_API_SECRET)
    parser.add_argument("--user-id", dest="user_id", help="测试用户外部唯一标识", default=DEFAULT_USER_ID)
    parser.add_argument("--base-url", dest="base_url", help="API基础URL", default=DEFAULT_BASE_URL)
    
    # 操作动作
    parser.add_argument("--list", action="store_true", help="仅获取并打印当前机构所有智能体列表")
    parser.add_argument("--greet-all", action="store_true", help="遍历所有智能体逐一发送问候语")
    parser.add_argument("--limit", type=int, help="遍历发送时的最大智能体数量限制 (可选)")
    parser.add_argument("--send", action="store_true", help="单独向指定智能体发送一条消息")
    parser.add_argument("--bot-id", type=int, help="目标智能体ID (配合 --send 使用)")
    parser.add_argument("--msg", default="你好！很高兴认识你。", help="发送的消息内容 (配合 --send 或 --greet-all 使用)")

    args = parser.parse_args()

    client = BotChatClient(args.api_key, args.api_secret, base_url=args.base_url)

    print(f"[1] 正在通过 apiKey ({client.api_key}) 为用户 '{args.user_id}' 换取访问令牌...")
    try:
        token = client.auth_user(args.user_id)
        print(f"状态：成功 (Token: {token[:10]}...{token[-6:]})")
    except Exception as e:
        print(f"状态：失败，认证异常: {e}")
        sys.exit(1)

    # 1. 列表模式
    if args.list:
        print("\n[2] 正在拉取当前机构所有可用智能体列表...")
        bots = client.get_bot_list()
        print(f"状态：成功，当前机构可用智能体共 {len(bots)} 个：\n")
        for i, b in enumerate(bots, 1):
            print(f"[{i}] 【{b.get('name')}】(ID: {b.get('id')})")
            print(f"    * 角色定位: {b.get('position', '无')}")
            print(f"    * 开场白:   {b.get('greeting', '无')}")
            print(f"    * 标签特长: {b.get('proficient', '无')}")
        return

    # 2. 单发模式
    if args.send:
        if not args.bot_id:
            print("[ERROR] 单独发送消息必须指定 --bot-id，例如: --send --bot-id 265 --msg '你好'")
            sys.exit(1)
        print(f"\n[2] 正在向智能体 (ID: {args.bot_id}) 单独发送消息: '{args.msg}'...")
        reply = client.send_message(args.bot_id, args.msg)
        print(f"状态：成功\n智能体回复内容:\n{reply}")
        return

    # 3. 默认或显式执行遍历问候模式
    print("\n[2] 执行遍历智能体发送问候语...")
    client.greet_all_bots(greeting_text=args.msg, limit=args.limit)


if __name__ == "__main__":
    main()
