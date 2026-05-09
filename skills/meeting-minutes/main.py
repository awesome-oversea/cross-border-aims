#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Meeting Minutes Generator - B7-05

Accepts meeting transcript text, extracts topics/decisions/action items,
generates structured meeting minutes. Optionally stores to MySQL via data-layer.
"""
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Data-layer for optional MySQL storage
try:
    import importlib.util
    _dl_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-layer', 'main.py'))
    _dl_spec = importlib.util.spec_from_file_location("mm_dl", _dl_path)
    if _dl_spec:
        _dl_mod = importlib.util.module_from_spec(_dl_spec)
        sys.modules["mm_dl"] = _dl_mod
        _dl_spec.loader.exec_module(_dl_mod)
        _dl = _dl_mod
        _dl_available = True
    else:
        _dl_available = False
except Exception:
    _dl_available = False

# Patterns for extracting structured information from transcripts
TOPIC_PATTERNS = [
    r"(?i)(?:议题|讨论|agenda|topic)\s*[：:]\s*(.+)",
    r"(?i)(?:接下来|下面|然后|next|then)\s*(?:我们|咱们|大家)?\s*(?:讨论|讲|说|看|聊)?\s*(?:一下|一?)?(.+)",
    r"(?i)^(?:关于|regarding|re:)\s+(.+)",
    r"(?i)(?:第一|第二|第三|首先|其次|最后)\s*(?:个?[：:]?\s*)(.+)",
]

DECISION_PATTERNS = [
    r"(?i)(?:决定|决策|确定|确认|同意|批准|定稿|conclude|decide|agree|approve|confirm)\s*(?:[：:]\s*|了\s*)(.+)",
    r"(?i)(?:就这么办|就这样|that's settled|deal|done|agreed)",
    r"(?i)(?:最终|最终决定|final decision|conclusion)\s*(?:[：:]\s*)(.+)",
    r"(?i)(?:一致同意|unanimously)\s*(.+)",
]

ACTION_ITEM_PATTERNS = [
    r"(?i)(?:待办|todo|action\s*item|to-do|to\s*do|owner|负责人|assignee)\s*(?:[：:]\s*)?(.+)",
    r"(?i)(?:需要|需|must|should|need\s+to|have\s+to)\s*(?:我们|你|您|大家)?\s*(.+)",
    r"(?i)(?:负责|responsible|owned\s+by)\s*(?:[：:]\s*)?(.+)",
    r"(?i)(?:由谁|谁负责|who)\s*(.+)",
    r"(?i)(?:deadline|截止|ddl|due\s*date)\s*(?:[：:]\s*)?(.+)",
]

DEADLINE_PATTERNS = [
    r"(?i)(?:下周[一二三四五六日]|this\s+week|next\s+week|tomorrow|today)",
    r"(?:(\d{4}[-/]\d{1,2}[-/]\d{1,2}))",
    r"(?i)(?:周[一二三四五六日]|周[1-7])",
]

PARTICIPANT_PATTERNS = [
    r"(?i)(?:参会|参与|出席|参加|attendee|participant)\s*(?:人员|人|者)?\s*(?:[：:]\s*)?(.+)",
    r"(?i)(?:与会|present)\s*(?:人员|人)?\s*(?:[：:]\s*)?(.+)",
    r"(?i)(?:主持人|moderator|chair)\s*(?:[：:]\s*)?(.+)",
]


def extract_topics(transcript: str) -> List[Dict]:
    """Extract discussion topics from transcript."""
    topics = []
    seen = set()
    lines = transcript.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue
        for pattern in TOPIC_PATTERNS:
            m = re.search(pattern, line)
            if m:
                title = m.group(1).strip().rstrip('。，,.').strip()
                if title and title not in seen and len(title) > 2:
                    seen.add(title)
                    # Extract discussion content (lines after this topic mention)
                    discussion = []
                    for subsequent_line in lines[lines.index(line) + 1:lines.index(line) + 6]:
                        s = subsequent_line.strip()
                        if s and not any(re.search(p, s) for p in TOPIC_PATTERNS):
                            discussion.append(s)
                    topics.append({
                        "title": title,
                        "discussion": discussion if discussion else [],
                    })
                    break
    return topics


def extract_decisions(transcript: str) -> List[str]:
    """Extract decisions made during the meeting."""
    decisions = []
    seen = set()
    for line in transcript.split('\n'):
        line = line.strip()
        if not line:
            continue
        for pattern in DECISION_PATTERNS:
            m = re.search(pattern, line)
            if m:
                text = m.group(1).strip() if m.lastindex and m.group(1) else line.strip()
                if text and text not in seen and len(text) > 3:
                    seen.add(text)
                    decisions.append(text)
                    break
    return decisions


def extract_action_items(transcript: str) -> List[Dict]:
    """Extract action items with owners and deadlines."""
    items = []
    current_item = None

    for line in transcript.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check for action item mention
        for pattern in ACTION_ITEM_PATTERNS:
            m = re.search(pattern, line)
            if m and not current_item:
                task = m.group(1).strip() if m.lastindex and m.group(1) else line.strip()
                current_item = {"task": task, "owner": "", "deadline": ""}
                break

        if current_item:
            # Look for owner mention
            if not current_item["owner"]:
                owner_m = re.search(r"(?i)(?:负责人|owner|assignee|由谁|谁负责|responsible)\s*(?:[：:]\s*)?(\S+)", line)
                if not owner_m:
                    owner_m = re.search(r"(?:@|\/\/)\s*(\S+)", line)
                if owner_m:
                    current_item["owner"] = owner_m.group(1).strip()

            # Look for deadline
            if not current_item["deadline"]:
                for dp in DEADLINE_PATTERNS:
                    dm = re.search(dp, line)
                    if dm:
                        current_item["deadline"] = dm.group(0) if dm.lastindex else dm.group(0)
                        break

            # End of current action item (next action pattern or empty section)
            next_action = any(re.search(p, line) for p in ACTION_ITEM_PATTERNS[:2])
            if next_action and current_item["task"] != line:
                if current_item not in items:
                    items.append(current_item)
                current_item = None

    if current_item and current_item not in items:
        items.append(current_item)

    return items


def generate_summary(transcript: str, topics: List[Dict], decisions: List[str]) -> str:
    """Generate a brief meeting summary."""
    word_count = len(transcript)
    topic_count = len(topics)
    decision_count = len(decisions)
    topic_names = [t["title"] for t in topics[:3]]

    parts = [f"本次会议共讨论{topic_count}个议题"]
    if topic_names:
        parts.append(f"，涉及：{'、'.join(topic_names)}")
    if decision_count > 0:
        parts.append(f"。形成{decision_count}项决策")
    parts.append(f"。会议记录约{word_count}字。")

    return ''.join(parts)


def estimate_duration(transcript: str) -> str:
    """Roughly estimate meeting duration based on transcript length."""
    word_count = len(transcript)
    # Assuming ~200 words per minute
    minutes = max(5, round(word_count / 200 / 5) * 5)
    if minutes >= 60:
        return f"{minutes // 60}小时{minutes % 60}分钟"
    return f"{minutes}分钟"


def generate_minutes(input_data: Dict) -> Dict:
    """Generate structured meeting minutes from transcript."""
    transcript = input_data.get("transcript", "")
    if not transcript:
        return {"error": "缺少 transcript（会议记录文本）"}

    meeting_title = input_data.get("meeting_title", "会议纪要")
    meeting_date = input_data.get("meeting_date", datetime.now().strftime("%Y-%m-%d"))
    participants_raw = input_data.get("participants", [])

    # Extract structured info
    topics = extract_topics(transcript)
    decisions = extract_decisions(transcript)
    action_items = extract_action_items(transcript)
    summary = generate_summary(transcript, topics, decisions)
    duration = estimate_duration(transcript)

    # Try to extract participants from transcript if not provided
    participants = list(participants_raw) if isinstance(participants_raw, list) else []
    if not participants:
        for line in transcript.split('\n'):
            for pattern in PARTICIPANT_PATTERNS:
                m = re.search(pattern, line)
                if m:
                    extracted = m.group(1).strip()
                    parts = re.split(r'[,，、\s]+', extracted)
                    for p in parts:
                        p = p.strip()
                        if p and p not in participants and len(p) > 1:
                            participants.append(p)
                    break

    minutes = {
        "meeting_title": meeting_title,
        "date": meeting_date,
        "participants": participants,
        "duration_estimate": duration,
        "summary": summary,
        "topics": topics,
        "decisions": decisions,
        "action_items": action_items,
        "next_steps": [a["task"] for a in action_items if a.get("owner")],
    }

    # Optionally store to MySQL
    if input_data.get("store") and _dl_available:
        try:
            dm = _dl.DataManager()
            dm.insert_record("contents", {
                "content_id": f"mtg-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "type": "meeting_minutes",
                "platform": "internal",
                "title": meeting_title,
                "content": json.dumps(minutes, ensure_ascii=False),
                "status": "published",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            minutes["stored"] = True
        except Exception:
            minutes["stored"] = False

    return minutes


def main():
    input_data = json.loads(sys.stdin.read())
    result = generate_minutes(input_data)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
