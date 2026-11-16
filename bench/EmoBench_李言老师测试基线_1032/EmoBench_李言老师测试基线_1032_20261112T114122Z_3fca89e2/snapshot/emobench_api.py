"""Independent agent API transport for EmoBench, derived from audited local transport.

Handles unified JSON business errors, double-encoded SSE, raw audit files.
Authentication payloads and bearer values are never written to artifacts.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import requests

def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_json(path, value):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class APIError(RuntimeError):
    pass


class ProtocolError(RuntimeError):
    pass


def unpack(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        message = payload.get("message") if isinstance(payload, dict) else "响应不是对象"
        code = payload.get("code") if isinstance(payload, dict) else None
        raise APIError(f"业务错误 code={code}: {message}")
    return payload.get("data")


def sse_events(lines):
    """Parse event boundaries, multiline data and a final event without blank line."""
    data, event_type = [], "message"
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line == "":
            if data:
                yield event_type, "\n".join(data)
            data, event_type = [], "message"
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
        elif line.startswith("event:"):
            event_type = line[6:].strip()
    if data:
        yield event_type, "\n".join(data)


def parse_sse(lines, event_sink):
    pieces, metadata = [], {"models": [], "conversation_ids": [], "finish_seen": False}
    for event_type, data in sse_events(lines):
        if data.strip() == "[DONE]":
            metadata["finish_seen"] = True
            event_sink({"event": event_type, "data": "[DONE]"})
            break
        obj = json.loads(data)
        if isinstance(obj, str):
            obj = json.loads(obj)
        event_sink({"event": event_type, "data": obj})
        if not isinstance(obj, dict):
            raise ProtocolError("SSE data 解码后不是对象")
        choices = obj.get("choices") or []
        choice = choices[0] if choices else {}
        delta = choice.get("delta") or {}
        if obj.get("model") == "error" or obj.get("success") is False or event_type == "error":
            raise APIError(str(delta.get("content") or obj.get("message") or obj.get("error") or "SSE error"))
        for source, key in (("model", "models"), ("conversationId", "conversation_ids")):
            if obj.get(source) is not None and obj[source] not in metadata[key]:
                metadata[key].append(obj[source])
        if obj.get("type") not in ("tts", "tts.error") and delta.get("content"):
            if not isinstance(delta["content"], str):
                raise ProtocolError("delta.content 不是字符串")
            pieces.append(delta["content"])
        if choice.get("finishReason") == "stop" or choice.get("finish_reason") == "stop":
            metadata["finish_seen"] = True
            break
    if not metadata["finish_seen"]:
        raise ProtocolError("流在结束标记前关闭，保留原始响应但不计为完整答案")
    return "".join(pieces).strip(), metadata


class Client:
    def __init__(self, base_url, key, secret, user_id, verify=True, timeout=60):
        self.base_url = base_url.rstrip("/") + "/psychology-api"
        self.key, self.secret, self.user_id = key, secret, user_id
        self.verify, self.timeout = verify, timeout
        self.session = requests.Session()
        self.session.trust_env = False
        self.token = None

    def authenticate(self):
        # Do not log authentication input/output; both contain credentials.
        with self.session.post(self.base_url + "/apis/auth", json={
            "apiKey": self.key, "apiSecret": self.secret, "userId": self.user_id,
        }, timeout=(10, self.timeout), verify=self.verify) as response:
            response.raise_for_status()
            data = unpack(response.json())
            if not isinstance(data, dict) or not data.get("access_token"):
                raise APIError("认证未返回 access_token")
            self.token = data["access_token"]

    def call(self, method, endpoint, directory, name, payload=None, params=None, chat=False):
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / f"{name}.request.json", {
            "timestamp": now(), "method": method, "url": self.base_url + endpoint,
            "json": payload, "params": params, "authentication": "Bearer [NOT SAVED]",
        })
        start = time.monotonic()
        with self.session.request(method, self.base_url + endpoint, json=payload, params=params,
                                  headers={"Authorization": f"Bearer {self.token}"},
                                  stream=True, timeout=(10, self.timeout), verify=self.verify) as response:
            write_json(directory / f"{name}.response.json", {
                "status_code": response.status_code, "content_type": response.headers.get("content-type"),
                "headers_seconds": time.monotonic() - start,
            })
            raw_path = directory / f"{name}.body.bin"
            if chat and response.ok and "text/event-stream" in response.headers.get("content-type", "").lower():
                # Save the body before parsing so malformed/failed events remain auditable.
                # Only received chunks are saved if the request times out.
                with raw_path.open("wb") as raw:
                    def lines():
                        buffer = b""
                        for chunk in response.iter_content(chunk_size=1024):
                            raw.write(chunk)
                            raw.flush()
                            if time.monotonic() - start > max(120, self.timeout * 3):
                                raise TimeoutError("SSE 总时长超限")
                            buffer += chunk
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                yield line.rstrip(b"\r").decode("utf-8")
                        if buffer:
                            yield buffer.rstrip(b"\r").decode("utf-8")
                    return parse_sse(lines(), lambda event: append_json(directory / f"{name}.events.jsonl", event))
            with raw_path.open("wb") as raw:
                for chunk in response.iter_content(chunk_size=8192):
                    raw.write(chunk)
            response.raise_for_status()
            body = json.loads(raw_path.read_bytes())
            data = unpack(body)
            if chat:
                if not isinstance(data, dict) or not isinstance(data.get("content"), str):
                    raise ProtocolError("聊天响应缺少字符串 data.content")
                return data["content"].strip(), {"response_source": data.get("responseSource"),
                                                "chat_id": data.get("chatId"), "finish_seen": True}
            return data

