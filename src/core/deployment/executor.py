"""
部署引擎模块

设计要点:
- 每步成功后再执行下一步 (串行执行)
- 实时日志记录
- 失败时触发 AI 排错
- 支持回滚
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeployStep:
    """部署步骤"""
    number: int
    description: str
    command: Optional[str] = None  # 可能没有命令，只是检查
    expected_output: Optional[str] = None

    # 执行结果
    status: str = "pending"  # pending, running, success, failed, skipped
    output: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class DeployPlan:
    """部署计划"""
    github_url: str
    service_type: str
    steps: List[DeployStep] = field(default_factory=list)
    current_step: int = 0

    @property
    def is_complete(self) -> bool:
        return all(s.status == "success" for s in self.steps)

    @property
    def has_failed(self) -> bool:
        return any(s.status == "failed" for s in self.steps)


class DeployExecutor:
    """部署执行器"""

    def __init__(self, ssh_client, ai_debugger=None):
        self.ssh_client = ssh_client
        self.ai_debugger = ai_debugger

    async def execute_plan(
        self,
        plan: DeployPlan,
        on_step_complete: Optional[Callable] = None
    ) -> bool:
        """
        串行执行部署计划

        Args:
            plan: 部署计划
            on_step_complete: 每步完成后的回调

        Returns:
            部署成功与否
        """
        for i, step in enumerate(plan.steps):
            plan.current_step = i

            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")

            # 执行步骤
            success = await self._execute_step(step)

            # 回调
            if on_step_complete:
                await on_step_complete(step)

            # 串行执行：只有成功才继续
            if not success:
                logger.error(f"Step {i+1} failed, stopping deployment")

                # 触发 AI 排错
                if self.ai_debugger:
                    debug_result = await self.ai_debugger.analyze(
                        failed_step=step,
                        previous_steps=plan.steps[:i]
                    )
                    logger.info(f"AI Debug: {debug_result.get('analysis', 'N/A')}")

                return False

        logger.info("Deployment completed successfully")
        return True

    async def _execute_step(self, step: DeployStep) -> bool:
        """执行单个步骤"""
        import time
        start_time = time.time()

        step.status = "running"

        if not step.command:
            # 无命令的步骤 (可能是检查点)
            step.status = "success"
            return True

        try:
            result = await self.ssh_client.execute(step.command)

            step.output = result["stdout"]
            step.duration_ms = result["duration_ms"]

            if result["exit_code"] == 0:
                step.status = "success"
                return True
            else:
                step.status = "failed"
                step.error_message = result["stderr"]
                return False

        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            return False

        finally:
            step.duration_ms = int((time.time() - start_time) * 1000)

    async def rollback(self, plan: DeployPlan) -> bool:
        """回滚部署"""
        logger.info("Rolling back deployment")

        # 反向执行已成功的步骤
        for step in reversed(plan.steps):
            if step.status != "success":
                continue

            rollback_command = self._generate_rollback_command(step.command)
            if rollback_command:
                logger.info(f"Rollback step: {step.description}")
                try:
                    await self.ssh_client.execute(rollback_command)
                except Exception as e:
                    logger.warning(f"Rollback step failed: {e}")

        return True

    def _generate_rollback_command(self, command: str) -> Optional[str]:
        """根据原命令生成回滚命令"""
        if not command:
            return None

        # 简单实现，实际使用需要更复杂的映射
        rollback_map = {
            "apt install": "apt remove -y",
            "apt-get install": "apt-get remove -y",
            "npm install": "rm -rf node_modules",
            "pip install": "pip uninstall -y",
            "systemctl enable": "systemctl disable",
            "systemctl start": "systemctl stop",
        }

        for orig, rollback in rollback_map.items():
            if command.startswith(orig):
                return command.replace(orig, rollback, 1)

        return None
