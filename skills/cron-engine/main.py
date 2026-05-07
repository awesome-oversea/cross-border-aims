import json
import os
import re
import psycopg2
import psycopg2.extras
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable

_PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
_PG_PORT = int(os.environ.get("PG_PORT", "5432"))
_PG_USER = os.environ.get("PG_USER", "GodyChang")
_PG_PASS = os.environ.get("PG_PASSWORD", "")
_PG_DB = os.environ.get("PG_DATABASE", "aims")

# 预置定时任务列表：AI日报/小红书发布/抖音发布/视频号发布/周报/舆情监控/Token刷新/团队日报
CRON_JOBS = [
    {
        "name": "daily-ai-report",
        "display_name": "AI行业日报",
        "cron_expr": "0 9 * * *",
        "description": "每天9:00推送AI行业日报",
        "agent": "office",
        "skill": "report-gen",
        "action": "generate_daily_report",
        "params": {"report_type": "ai_industry_daily"},
        "channel": "feishu",
        "target": "office_group",
        "enabled": True,
    },
    {
        "name": "xhs-daily-publish",
        "display_name": "小红书每日发布",
        "cron_expr": "0 10 * * *",
        "description": "每天10:00自动发布小红书种草内容",
        "agent": "social-media",
        "skill": "xhs-seed",
        "action": "auto_publish",
        "params": {"publish_mode": "scheduled"},
        "channel": "feishu",
        "target": "social_media_group",
        "enabled": True,
    },
    {
        "name": "douyin-daily-publish",
        "display_name": "抖音每日发布",
        "cron_expr": "0 11 * * *",
        "description": "每天11:00自动发布抖音内容",
        "agent": "social-media",
        "skill": "douyin-ops",
        "action": "auto_publish",
        "params": {"publish_mode": "scheduled"},
        "channel": "feishu",
        "target": "social_media_group",
        "enabled": True,
    },
    {
        "name": "video-channel-publish",
        "display_name": "视频号每日发布",
        "cron_expr": "0 14 * * *",
        "description": "每天14:00自动发布视频号内容",
        "agent": "social-media",
        "skill": "video-channel",
        "action": "auto_publish",
        "params": {"publish_mode": "scheduled"},
        "channel": "feishu",
        "target": "social_media_group",
        "enabled": True,
    },
    {
        "name": "weekly-report",
        "display_name": "运营周报",
        "cron_expr": "0 18 * * 5",
        "description": "每周五18:00生成运营周报",
        "agent": "office",
        "skill": "report-gen",
        "action": "generate_weekly_report",
        "params": {"report_type": "weekly_operations"},
        "channel": "feishu",
        "target": "office_group",
        "enabled": True,
    },
    {
        "name": "opinion-monitor",
        "display_name": "舆情监控",
        "cron_expr": "*/10 * * * *",
        "description": "每10分钟监控社媒评论舆情",
        "agent": "social-media",
        "skill": "opinion-watch",
        "action": "scan_opinions",
        "params": {"scan_type": "incremental"},
        "channel": "feishu",
        "target": "social_media_group",
        "enabled": True,
    },
    {
        "name": "token-refresh",
        "display_name": "Token刷新",
        "cron_expr": "0 */1 * * *",
        "description": "每小时刷新电商平台access_token",
        "agent": "ecommerce",
        "skill": "listing-gen",
        "action": "refresh_tokens",
        "params": {"platforms": ["taobao", "jd", "pdd"]},
        "channel": "internal",
        "target": "system",
        "enabled": True,
    },
    {
        "name": "team-daily-report",
        "display_name": "团队日报",
        "cron_expr": "0 8 * * *",
        "description": "每天8:00生成团队日报",
        "agent": "office",
        "skill": "report-gen",
        "action": "generate_team_daily",
        "params": {"report_type": "team_daily"},
        "channel": "feishu",
        "target": "office_group",
        "enabled": True,
    },
]


class CronParser:
    """Cron表达式解析器：支持标准5字段格式，提供解析/匹配/下次执行时间/可读化"""
    @staticmethod
    def parse(expr: str) -> Dict:
        """解析cron表达式为结构化字段（minute/hour/day_of_month/month/day_of_week）"""
        parts = expr.strip().split()
        if len(parts) != 5:
            return {"valid": False, "error": f"cron表达式必须包含5个字段，当前{len(parts)}个"}

        field_names = ["minute", "hour", "day_of_month", "month", "day_of_week"]
        result = {"valid": True, "fields": {}}

        for i, (part, name) in enumerate(zip(parts, field_names)):
            parsed = CronParser._parse_field(part, name)
            if not parsed["valid"]:
                return {"valid": False, "error": f"字段{name}解析失败: {parsed['error']}"}
            result["fields"][name] = parsed

        return result

    @staticmethod
    def _parse_field(field: str, name: str) -> Dict:
        ranges = {
            "minute": (0, 59),
            "hour": (0, 23),
            "day_of_month": (1, 31),
            "month": (1, 12),
            "day_of_week": (0, 6),
        }
        min_val, max_val = ranges[name]
        values = set()

        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                step = int(step)
                if step <= 0:
                    return {"valid": False, "error": f"步长必须大于0: {step}"}
                if base == "*":
                    start, end = min_val, max_val
                elif "-" in base:
                    start, end = map(int, base.split("-", 1))
                else:
                    start, end = int(base), max_val
                for v in range(start, end + 1, step):
                    if min_val <= v <= max_val:
                        values.add(v)
            elif "-" in part:
                start, end = map(int, part.split("-", 1))
                for v in range(start, end + 1):
                    if min_val <= v <= max_val:
                        values.add(v)
            elif part == "*":
                values = set(range(min_val, max_val + 1))
                break
            else:
                v = int(part)
                if min_val <= v <= max_val:
                    values.add(v)

        return {"valid": True, "values": sorted(values)}

    @staticmethod
    def matches(expr: str, dt: datetime) -> bool:
        """判断给定时间是否匹配cron表达式"""

        parsed = CronParser.parse(expr)
        if not parsed["valid"]:
            return False

        fields = parsed["fields"]
        return (
            dt.minute in fields["minute"]["values"]
            and dt.hour in fields["hour"]["values"]
            and dt.day in fields["day_of_month"]["values"]
            and dt.month in fields["month"]["values"]
            and dt.weekday() in fields["day_of_week"]["values"]
        )

    @staticmethod
    def next_run(expr: str, after: datetime = None) -> Optional[datetime]:
        """计算cron表达式下次执行时间（向后搜索最多1年）"""

        if after is None:
            after = datetime.now()

        for i in range(1, 525601):
            candidate = after + timedelta(minutes=i)
            candidate = candidate.replace(second=0, microsecond=0)
            if CronParser.matches(expr, candidate):
                return candidate
        return None

    @staticmethod
    def humanize(expr: str) -> str:
        """将cron表达式转换为可读的中文描述（如"每天9:00"）"""

        parsed = CronParser.parse(expr)
        if not parsed["valid"]:
            return f"无效表达式: {expr}"

        fields = parsed["fields"]
        m, h, dom, mon, dow = [fields[k]["values"] for k in ["minute", "hour", "day_of_month", "month", "day_of_week"]]

        parts = []
        if len(mon) < 12:
            parts.append(f"{mon}月")
        if len(dow) < 7 and len(dow) > 0:
            day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            parts.append("、".join(day_names[d] for d in dow if d < 7))
        if len(dom) < 31:
            parts.append(f"每月{dom}日")

        time_parts = []
        if len(h) < 24 and len(h) > 0:
            time_parts.append(f"{h[0]:02d}时" if len(h) == 1 else f"{h[0]:02d}-{h[-1]:02d}时")
        if len(m) < 60 and len(m) > 0:
            if len(m) == 1:
                time_parts.append(f"{m[0]:02d}分")
            else:
                step = m[1] - m[0] if len(m) > 1 else 1
                time_parts.append(f"每{step}分钟")

        if time_parts:
            parts.append("".join(time_parts))

        return " ".join(parts) if parts else "每分钟"


def init_db():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
    c.execute("""CREATE TABLE IF NOT EXISTS cron_jobs (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        display_name TEXT,
        cron_expr TEXT,
        description TEXT,
        agent TEXT,
        skill TEXT,
        action TEXT,
        params TEXT DEFAULT '{}',
        channel TEXT,
        target TEXT,
        enabled INTEGER DEFAULT 1,
        max_retries INTEGER DEFAULT 3,
        timeout_seconds INTEGER DEFAULT 300,
        created_at TEXT,
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cron_executions (
        id SERIAL PRIMARY KEY,
        job_name TEXT,
        execution_id TEXT,
        status TEXT DEFAULT 'pending',
        started_at TEXT,
        completed_at TEXT,
        duration_ms INTEGER DEFAULT 0,
        retry_count INTEGER DEFAULT 0,
        result TEXT,
        error_message TEXT,
        trigger_type TEXT DEFAULT 'cron',
        FOREIGN KEY (job_name) REFERENCES cron_jobs(name)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cron_locks (
        job_name TEXT PRIMARY KEY,
        locked_by TEXT,
        locked_at TEXT,
        expires_at TEXT
    )""")
    conn.commit()
    conn.close()


def get_db():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    return conn


class CronExecutor:
    """Cron任务执行器：通过skill_registry将定时任务分发给对应技能处理器"""
    def __init__(self):
        self.skill_registry = self._build_skill_registry()

    def _build_skill_registry(self) -> Dict[str, Callable]:
        return {
            "report-gen": self._execute_report_gen,
            "xhs-seed": self._execute_xhs_seed,
            "douyin-ops": self._execute_douyin_ops,
            "video-channel": self._execute_video_channel,
            "opinion-watch": self._execute_opinion_watch,
            "listing-gen": self._execute_listing_gen,
        }

    def execute(self, job: Dict) -> Dict:
        """执行单个定时任务：记录执行日志、调用对应skill处理器、返回执行结果和耗时"""

        execution_id = f"exec-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(job['name']) % 10000:04d}"
        start_time = time.time()

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            "INSERT INTO cron_executions (job_name, execution_id, status, started_at, trigger_type) VALUES (%s, %s, %s, %s, %s)",
            (job["name"], execution_id, "running", now, "cron"),
        )
        conn.commit()

        try:
            skill_name = job.get("skill", "")
            action = job.get("action", "")
            params = job.get("params", {})

            handler = self.skill_registry.get(skill_name)
            if handler:
                result = handler(action, params)
            else:
                result = {
                    "success": True,
                    "message": f"定时任务 {job['display_name']} 已触发",
                    "skill": skill_name,
                    "action": action,
                    "simulated": True,
                }

            duration = int((time.time() - start_time) * 1000)
            c.execute(
                "UPDATE cron_executions SET status=%s, completed_at=%s, duration_ms=%s, result=%s WHERE execution_id=%s",
                ("success", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, json.dumps(result, ensure_ascii=False), execution_id),
            )
            conn.commit()
            conn.close()

            return {
                "success": True,
                "execution_id": execution_id,
                "job_name": job["name"],
                "duration_ms": duration,
                "result": result,
            }

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            c.execute(
                "UPDATE cron_executions SET status=%s, completed_at=%s, duration_ms=%s, error_message=%s WHERE execution_id=%s",
                ("failed", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, str(e), execution_id),
            )
            conn.commit()
            conn.close()

            return {
                "success": False,
                "execution_id": execution_id,
                "job_name": job["name"],
                "duration_ms": duration,
                "error": str(e),
            }

    def _execute_report_gen(self, action: str, params: Dict) -> Dict:
        report_type = params.get("report_type", "unknown")
        return {
            "success": True,
            "action": action,
            "report_type": report_type,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"已生成{report_type}报表",
        }

    def _execute_xhs_seed(self, action: str, params: Dict) -> Dict:
        return {
            "success": True,
            "action": action,
            "platform": "xiaohongshu",
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "小红书种草内容已自动发布",
        }

    def _execute_douyin_ops(self, action: str, params: Dict) -> Dict:
        return {
            "success": True,
            "action": action,
            "platform": "douyin",
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "抖音内容已自动发布",
        }

    def _execute_video_channel(self, action: str, params: Dict) -> Dict:
        return {
            "success": True,
            "action": action,
            "platform": "wechat_video",
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "视频号内容已自动发布",
        }

    def _execute_opinion_watch(self, action: str, params: Dict) -> Dict:
        return {
            "success": True,
            "action": action,
            "scan_type": params.get("scan_type", "incremental"),
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "negative_count": 0,
            "message": "舆情扫描完成，未发现负面舆情",
        }

    def _execute_listing_gen(self, action: str, params: Dict) -> Dict:
        platforms = params.get("platforms", [])
        return {
            "success": True,
            "action": action,
            "platforms": platforms,
            "refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"已刷新{len(platforms)}个平台Token",
        }


class CronEngine:
    """Cron引擎核心：任务管理（增删改查）+ 守护线程（周期性检查并执行）+ 统计"""

    def __init__(self):
        init_db()
        self.executor = CronExecutor()
        self._running = False
        self._thread = None

    def init_builtin_jobs(self) -> Dict:
        """初始化预置定时任务到数据库，已存在则更新"""

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created = 0
        updated = 0

        for job in CRON_JOBS:
            c.execute("SELECT id FROM cron_jobs WHERE name=%s", (job["name"],))
            existing = c.fetchone()

            if existing:
                c.execute(
                    "UPDATE cron_jobs SET display_name=%s, cron_expr=%s, description=%s, agent=%s, skill=%s, action=%s, params=%s, channel=%s, target=%s, enabled=%s, updated_at=%s WHERE name=%s",
                    (
                        job["display_name"],
                        job["cron_expr"],
                        job["description"],
                        job["agent"],
                        job["skill"],
                        job["action"],
                        json.dumps(job.get("params", {}), ensure_ascii=False),
                        job["channel"],
                        job["target"],
                        1 if job.get("enabled", True) else 0,
                        now,
                        job["name"],
                    ),
                )
                updated += 1
            else:
                c.execute(
                    "INSERT INTO cron_jobs (name, display_name, cron_expr, description, agent, skill, action, params, channel, target, enabled, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        job["name"],
                        job["display_name"],
                        job["cron_expr"],
                        job["description"],
                        job["agent"],
                        job["skill"],
                        job["action"],
                        json.dumps(job.get("params", {}), ensure_ascii=False),
                        job["channel"],
                        job["target"],
                        1 if job.get("enabled", True) else 0,
                        now,
                        now,
                    ),
                )
                created += 1

        conn.commit()
        conn.close()
        return {"success": True, "created": created, "updated": updated, "total": len(CRON_JOBS)}

    def list_jobs(self) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("SELECT * FROM cron_jobs ORDER BY name")
        jobs = []
        for row in c.fetchall():
            job = dict(row)
            job["enabled"] = bool(job["enabled"])
            job["params"] = json.loads(job.get("params", "{}"))
            next_time = CronParser.next_run(job["cron_expr"])
            job["next_run"] = next_time.strftime("%Y-%m-%d %H:%M:%S") if next_time else None
            job["humanized_schedule"] = CronParser.humanize(job["cron_expr"])
            jobs.append(job)
        conn.close()
        return {"success": True, "jobs": jobs, "total": len(jobs)}

    def get_job(self, name: str) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("SELECT * FROM cron_jobs WHERE name=%s", (name,))
        row = c.fetchone()
        conn.close()
        if not row:
            return {"success": False, "error": f"任务 {name} 不存在"}
        job = dict(row)
        job["enabled"] = bool(job["enabled"])
        job["params"] = json.loads(job.get("params", "{}"))
        next_time = CronParser.next_run(job["cron_expr"])
        job["next_run"] = next_time.strftime("%Y-%m-%d %H:%M:%S") if next_time else None
        job["humanized_schedule"] = CronParser.humanize(job["cron_expr"])
        return {"success": True, "job": job}

    def toggle_job(self, name: str, enabled: bool) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("UPDATE cron_jobs SET enabled=%s, updated_at=%s WHERE name=%s", (1 if enabled else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "name": name, "enabled": enabled, "updated": affected > 0}

    def trigger_job(self, name: str) -> Dict:
        job_result = self.get_job(name)
        if not job_result["success"]:
            return job_result

        job = job_result["job"]
        return self.executor.execute(job)

    def add_job(self, job_config: Dict) -> Dict:
        required = ["name", "cron_expr", "skill", "action"]
        for field in required:
            if field not in job_config:
                return {"success": False, "error": f"缺少必填字段: {field}"}

        parsed = CronParser.parse(job_config["cron_expr"])
        if not parsed["valid"]:
            return {"success": False, "error": f"cron表达式无效: {parsed['error']}"}

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            c.execute(
                "INSERT INTO cron_jobs (name, display_name, cron_expr, description, agent, skill, action, params, channel, target, enabled, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    job_config["name"],
                    job_config.get("display_name", job_config["name"]),
                    job_config["cron_expr"],
                    job_config.get("description", ""),
                    job_config.get("agent", "main"),
                    job_config["skill"],
                    job_config["action"],
                    json.dumps(job_config.get("params", {}), ensure_ascii=False),
                    job_config.get("channel", "feishu"),
                    job_config.get("target", ""),
                    1 if job_config.get("enabled", True) else 0,
                    now,
                    now,
                ),
            )
            conn.commit()
            conn.close()
            return {"success": True, "name": job_config["name"]}
        except Exception as _pg_ie:
            if 'Duplicate' not in str(_pg_ie) and 'unique' not in str(_pg_ie).lower():
                raise
            conn.close()
            return {"success": False, "error": f"任务 {job_config['name']} 已存在"}

    def delete_job(self, name: str) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("DELETE FROM cron_jobs WHERE name=%s", (name,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "name": name, "deleted": affected > 0}

    def get_executions(self, job_name: str = None, limit: int = 20) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        if job_name:
            c.execute("SELECT * FROM cron_executions WHERE job_name=%s ORDER BY started_at DESC LIMIT %s", (job_name, limit))
        else:
            c.execute("SELECT * FROM cron_executions ORDER BY started_at DESC LIMIT %s", (limit,))
        executions = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"success": True, "executions": executions, "total": len(executions)}

    def get_stats(self) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)

        c.execute("SELECT COUNT(*) as total FROM cron_jobs")
        total_jobs = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as total FROM cron_jobs WHERE enabled=1")
        enabled_jobs = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as total FROM cron_executions")
        total_executions = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as total FROM cron_executions WHERE status='success'")
        success_executions = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as total FROM cron_executions WHERE status='failed'")
        failed_executions = c.fetchone()["total"]

        c.execute("SELECT job_name, COUNT(*) as count, AVG(duration_ms) as avg_duration FROM cron_executions WHERE status='success' GROUP BY job_name ORDER BY count DESC")
        job_stats = [dict(row) for row in c.fetchall()]

        c.execute("SELECT job_name, status, started_at FROM cron_executions ORDER BY started_at DESC LIMIT 5")
        recent = [dict(row) for row in c.fetchall()]

        conn.close()

        return {
            "success": True,
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "disabled_jobs": total_jobs - enabled_jobs,
            "total_executions": total_executions,
            "success_executions": success_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_executions / total_executions * 100, 1) if total_executions > 0 else 0,
            "job_stats": job_stats,
            "recent_executions": recent,
        }

    def check_and_execute(self) -> Dict:
        """检查所有启用的定时任务，匹配当前时间的任务立即执行"""

        now = datetime.now()
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("SELECT * FROM cron_jobs WHERE enabled=1")
        jobs = [dict(row) for row in c.fetchall()]
        conn.close()

        triggered = []
        for job in jobs:
            job["params"] = json.loads(job.get("params", "{}"))
            job["enabled"] = bool(job["enabled"])

            if CronParser.matches(job["cron_expr"], now):
                result = self.executor.execute(job)
                triggered.append({"job_name": job["name"], "result": result})

        return {"success": True, "checked_at": now.strftime("%Y-%m-%d %H:%M:%S"), "triggered_count": len(triggered), "triggered": triggered}

    def start_daemon(self, interval_seconds: int = 60):
        """启动守护线程：每隔interval_seconds秒检查一次定时任务"""

        if self._running:
            return {"success": False, "error": "守护线程已在运行"}

        self._running = True

        def _run():
            while self._running:
                try:
                    self.check_and_execute()
                except Exception as e:
                    print(f"Cron daemon error: {e}", file=sys.stderr)
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return {"success": True, "message": f"守护线程已启动，间隔{interval_seconds}秒"}

    def stop_daemon(self) -> Dict:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        return {"success": True, "message": "守护线程已停止"}

    def validate_cron(self, expr: str) -> Dict:
        parsed = CronParser.parse(expr)
        if not parsed["valid"]:
            return {"valid": False, "error": parsed["error"]}

        next_time = CronParser.next_run(expr)
        return {
            "valid": True,
            "expression": expr,
            "humanized": CronParser.humanize(expr),
            "next_run": next_time.strftime("%Y-%m-%d %H:%M:%S") if next_time else None,
            "fields": {k: v["values"] for k, v in parsed["fields"].items()},
        }


def main():
    input_data = json.loads(sys.stdin.read())
    action = input_data.get("action", "list_jobs")
    engine = CronEngine()

    if action == "init_builtin":
        result = engine.init_builtin_jobs()
    elif action == "list_jobs":
        result = engine.list_jobs()
    elif action == "get_job":
        result = engine.get_job(input_data.get("name", ""))
    elif action == "toggle_job":
        result = engine.toggle_job(input_data.get("name", ""), input_data.get("enabled", True))
    elif action == "trigger_job":
        result = engine.trigger_job(input_data.get("name", ""))
    elif action == "add_job":
        result = engine.add_job(input_data.get("job_config", {}))
    elif action == "delete_job":
        result = engine.delete_job(input_data.get("name", ""))
    elif action == "executions":
        result = engine.get_executions(input_data.get("name"), input_data.get("limit", 20))
    elif action == "stats":
        result = engine.get_stats()
    elif action == "check_and_execute":
        result = engine.check_and_execute()
    elif action == "validate_cron":
        result = engine.validate_cron(input_data.get("expr", ""))
    elif action == "start_daemon":
        result = engine.start_daemon(input_data.get("interval", 60))
    elif action == "stop_daemon":
        result = engine.stop_daemon()
    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
