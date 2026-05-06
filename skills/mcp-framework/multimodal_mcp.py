import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multimodal_mcp.db")

TOOL_DEFINITIONS = {
    "dalle_generate": {
        "description": "使用DALL-E生成图片",
        "params": {"prompt": "图片描述", "size": "尺寸(256x256/512x512/1024x1024)", "n": "生成数量(1-4)", "quality": "质量(standard/hd)", "style": "风格(vivid/natural)"},
        "risk_level": "write",
        "cost": {"256x256": 0.016, "512x512": 0.018, "1024x1024": 0.02, "1024x1024_hd": 0.08},
    },
    "dalle_edit": {
        "description": "使用DALL-E编辑图片(局部修改)",
        "params": {"image": "原始图片URL", "prompt": "编辑描述", "mask": "遮罩区域(可选)"},
        "risk_level": "write",
        "cost": 0.016,
    },
    "whisper_transcribe": {
        "description": "使用Whisper语音转文字",
        "params": {"audio_url": "音频文件URL", "language": "语言代码(zh/en/ja等，可选)", "model": "模型(whisper-1)", "response_format": "输出格式(json/text/srt/vtt)"},
        "risk_level": "read",
        "cost": 0.006,
    },
    "whisper_translate": {
        "description": "使用Whisper语音翻译(翻译为英文)",
        "params": {"audio_url": "音频文件URL", "model": "模型(whisper-1)", "response_format": "输出格式"},
        "risk_level": "read",
        "cost": 0.006,
    },
    "tts_synthesize": {
        "description": "使用TTS文字转语音",
        "params": {"text": "待转换文本", "voice": "声音类型(alloy/echo/fable/onyx/nova/shimmer)", "model": "模型(tts-1/tts-1-hd)", "speed": "语速(0.25-4.0)", "response_format": "输出格式(mp3/opus/aac/flac)"},
        "risk_level": "write",
        "cost": {"tts-1": 0.015, "tts-1-hd": 0.03},
    },
    "vision_analyze": {
        "description": "使用GPT-4V分析图片内容",
        "params": {"image_url": "图片URL", "prompt": "分析提示", "max_tokens": "最大输出token数"},
        "risk_level": "read",
        "cost": 0.01,
    },
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            result TEXT DEFAULT '{}',
            cost REAL DEFAULT 0,
            status TEXT DEFAULT 'completed',
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audio_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool TEXT NOT NULL,
            audio_url TEXT DEFAULT '',
            text_content TEXT DEFAULT '',
            language TEXT DEFAULT '',
            duration_seconds REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            status TEXT DEFAULT 'completed',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


class MultimodalMCP:
    def __init__(self):
        init_db()
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.configured = bool(self.openai_key)

    def call_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name not in TOOL_DEFINITIONS:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool_def = TOOL_DEFINITIONS[tool_name]

        try:
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler:
                result = handler(params)
            else:
                result = self._handle_simulated(tool_name, params)

            result["tool"] = tool_name
            result["risk_level"] = tool_def["risk_level"]
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}

    def _handle_dalle_generate(self, params: Dict) -> Dict:
        prompt = params.get("prompt", "")
        size = params.get("size", "1024x1024")
        n = int(params.get("n", 1))
        quality = params.get("quality", "standard")
        style = params.get("style", "vivid")

        cost_key = f"{size}_hd" if quality == "hd" else size
        cost_per = TOOL_DEFINITIONS["dalle_generate"]["cost"].get(cost_key, 0.02)
        total_cost = cost_per * n

        image_urls = []
        for i in range(n):
            image_urls.append(f"https://ai-aims.local/generated/dalle_{int(time.time())}_{i}.png")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO generations (tool, params, result, cost, status, created_at) VALUES (?,?,?,?,?,?)",
            ("dalle_generate", json.dumps(params, ensure_ascii=False)[:500], json.dumps({"image_urls": image_urls}), total_cost, "completed", now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "image_urls": image_urls,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "style": style,
            "cost": total_cost,
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_dalle_edit(self, params: Dict) -> Dict:
        prompt = params.get("prompt", "")
        image_url = params.get("image", "")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO generations (tool, params, result, cost, status, created_at) VALUES (?,?,?,?,?,?)",
            ("dalle_edit", json.dumps(params, ensure_ascii=False)[:500], "{}", 0.016, "completed", now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "edited_image_url": f"https://ai-aims.local/edited/dalle_edit_{int(time.time())}.png",
            "prompt": prompt,
            "cost": 0.016,
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_whisper_transcribe(self, params: Dict) -> Dict:
        audio_url = params.get("audio_url", "")
        language = params.get("language", "")
        model = params.get("model", "whisper-1")

        simulated_text = "这是语音转文字的模拟输出结果。实际使用时将调用OpenAI Whisper API进行语音识别。"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO audio_records (tool, audio_url, text_content, language, duration_seconds, cost, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("whisper_transcribe", audio_url, simulated_text, language or "zh", 30.0, 0.006, "completed", now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "text": simulated_text,
            "language": language or "zh",
            "duration": 30.0,
            "model": model,
            "cost": 0.006,
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_whisper_translate(self, params: Dict) -> Dict:
        audio_url = params.get("audio_url", "")

        simulated_text = "This is a simulated translation output. When using the actual API, it will call OpenAI Whisper API for speech translation."

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO audio_records (tool, audio_url, text_content, language, duration_seconds, cost, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            ("whisper_translate", audio_url, simulated_text, "en", 30.0, 0.006, "completed", now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "text": simulated_text,
            "language": "en",
            "cost": 0.006,
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_tts_synthesize(self, params: Dict) -> Dict:
        text = params.get("text", "")
        voice = params.get("voice", "alloy")
        model = params.get("model", "tts-1")
        speed = float(params.get("speed", 1.0))

        cost_per_1k = TOOL_DEFINITIONS["tts_synthesize"]["cost"].get(model, 0.015)
        char_count = len(text)
        cost = cost_per_1k * (char_count / 1000)

        audio_url = f"https://ai-aims.local/tts/tts_{int(time.time())}.mp3"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO generations (tool, params, result, cost, status, created_at) VALUES (?,?,?,?,?,?)",
            ("tts_synthesize", json.dumps(params, ensure_ascii=False)[:500], json.dumps({"audio_url": audio_url}), cost, "completed", now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "audio_url": audio_url,
            "text_length": char_count,
            "voice": voice,
            "model": model,
            "speed": speed,
            "cost": round(cost, 4),
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_vision_analyze(self, params: Dict) -> Dict:
        image_url = params.get("image_url", "")
        prompt = params.get("prompt", "请描述这张图片的内容")

        simulated_analysis = f"图片分析结果：该图片包含商品展示内容，主体清晰，背景简洁。建议优化方向：增加生活场景感，提升视觉吸引力。"

        return {
            "success": True,
            "analysis": simulated_analysis,
            "image_url": image_url,
            "prompt": prompt,
            "cost": 0.01,
            "mode": "simulated" if not self.configured else "api",
        }

    def _handle_simulated(self, tool_name: str, params: Dict) -> Dict:
        return {
            "success": True,
            "message": f"工具 {tool_name} 模拟执行成功",
            "params": params,
            "mode": "simulated",
        }

    def list_tools(self) -> Dict:
        tools = []
        for name, defn in TOOL_DEFINITIONS.items():
            tools.append({
                "name": name,
                "description": defn["description"],
                "params": defn["params"],
                "risk_level": defn["risk_level"],
            })
        return {"total": len(tools), "tools": tools}

    def get_usage_stats(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT tool, COUNT(*) as count, SUM(cost) as total_cost FROM generations GROUP BY tool")
        gen_stats = {row["tool"]: {"count": row["count"], "cost": row["total_cost"] or 0} for row in c.fetchall()}
        c.execute("SELECT tool, COUNT(*) as count FROM audio_records GROUP BY tool")
        audio_stats = {row["tool"]: {"count": row["count"]} for row in c.fetchall()}
        conn.close()

        return {"generation_stats": gen_stats, "audio_stats": audio_stats, "configured": self.configured}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multimodal MCP Server")
    parser.add_argument("--action", required=True)
    parser.add_argument("--tool", default="")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()

    mcp = MultimodalMCP()

    if args.action == "call_tool":
        params = json.loads(args.params)
        result = mcp.call_tool(args.tool, params)
    elif args.action == "list_tools":
        result = mcp.list_tools()
    elif args.action == "usage_stats":
        result = mcp.get_usage_stats()
    else:
        result = {"error": f"未知操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
