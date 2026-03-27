"""
AI 使用成本追踪器
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Session

from src.db.database import Base


class AICostRecord(Base):
    """AI 使用成本记录"""
    __tablename__ = "ai_cost_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # 关联用户
    deployment_id = Column(Integer, ForeignKey("deployments.id"))  # 关联部署

    provider = Column(String(50))  # 使用的 Provider
    model = Column(String(100))    # 使用的模型

    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    cost_cny = Column(Float)  # 成本 (人民币)

    action_type = Column(String(50))  # parse_readme, debug, rag_search, chat
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CostTracker:
    """成本追踪器"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def record_usage(
        self,
        response: "LLMResponse",
        user_id: Optional[int] = None,
        deployment_id: Optional[int] = None,
        action_type: str = "unknown"
    ):
        """记录 AI 使用"""
        from .providers.base import LLMResponse

        record = AICostRecord(
            user_id=user_id,
            deployment_id=deployment_id,
            provider=response.provider.value,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            cost_cny=response.usage.cost_cny or 0,
            action_type=action_type
        )
        self.db.add(record)
        self.db.commit()

    def get_user_cost(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """获取用户成本统计"""
        query = self.db.query(AICostRecord).filter(AICostRecord.user_id == user_id)

        if start_date:
            query = query.filter(AICostRecord.created_at >= start_date)
        if end_date:
            query = query.filter(AICostRecord.created_at <= end_date)

        records = query.all()

        return {
            "total_cost_cny": sum(r.cost_cny for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "by_provider": self._group_by_provider(records),
            "by_action": self._group_by_action(records),
            "record_count": len(records)
        }

    def get_deployment_cost(self, deployment_id: int) -> Dict:
        """获取部署的 AI 成本"""
        records = self.db.query(AICostRecord).filter(
            AICostRecord.deployment_id == deployment_id
        ).all()

        return {
            "total_cost_cny": sum(r.cost_cny for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "record_count": len(records)
        }

    def get_daily_cost(
        self,
        days: int = 7
    ) -> List[Dict]:
        """获取每日成本统计"""
        start_date = datetime.utcnow() - timedelta(days=days)

        records = self.db.query(AICostRecord).filter(
            AICostRecord.created_at >= start_date
        ).all()

        # 按天分组
        daily_stats: Dict[str, Dict] = {}
        for r in records:
            day = r.created_at.strftime("%Y-%m-%d")
            if day not in daily_stats:
                daily_stats[day] = {"cost": 0, "tokens": 0}
            daily_stats[day]["cost"] += r.cost_cny
            daily_stats[day]["tokens"] += r.total_tokens

        return [
            {"date": date, **stats}
            for date, stats in sorted(daily_stats.items())
        ]

    def _group_by_provider(self, records: List[AICostRecord]) -> Dict:
        """按 Provider 分组统计"""
        result: Dict[str, Dict] = {}
        for r in records:
            if r.provider not in result:
                result[r.provider] = {"cost": 0, "tokens": 0}
            result[r.provider]["cost"] += r.cost_cny
            result[r.provider]["tokens"] += r.total_tokens
        return result

    def _group_by_action(self, records: List[AICostRecord]) -> Dict:
        """按操作类型分组统计"""
        result: Dict[str, Dict] = {}
        for r in records:
            if r.action_type not in result:
                result[r.action_type] = {"cost": 0, "tokens": 0, "count": 0}
            result[r.action_type]["cost"] += r.cost_cny
            result[r.action_type]["tokens"] += r.total_tokens
            result[r.action_type]["count"] += 1
        return result

    def get_total_cost_today(self) -> float:
        """获取今日总成本"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = self.db.query(func.sum(AICostRecord.cost_cny)).filter(
            AICostRecord.created_at >= today_start
        ).scalar()

        return float(result) if result else 0.0
