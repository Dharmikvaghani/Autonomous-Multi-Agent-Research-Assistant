import asyncio
import uuid
import time
from typing import Dict, Any, List, AsyncGenerator
from orchestrators.agent_orchestrator import AgentOrchestrator

class ResearchTask:
    def __init__(self, task_id: str, topic: str, workspace: str, self_correction_rounds: int = 1):
        self.task_id = task_id
        self.topic = topic
        self.workspace = workspace
        self.self_correction_rounds = self_correction_rounds
        self.status = "PENDING"
        self.logs: List[str] = []
        self.listeners: List[asyncio.Queue] = []
        self.orchestrator: AgentOrchestrator = None
        self.result: Dict[str, Any] = {}
        self.created_at = time.time()
        self.duration = 0.0

    def add_log(self, log_msg: str):
        self.logs.append(log_msg)
        # Notify all active SSE queues
        event_data = {
            "type": "log",
            "task_id": self.task_id,
            "status": self.status,
            "message": log_msg,
            "timestamp": time.time()
        }
        for q in list(self.listeners):
            try:
                q.put_nowait(event_data)
            except Exception:
                pass

class ResearchService:
    def __init__(self):
        self.tasks: Dict[str, ResearchTask] = {}

    def create_task(self, topic: str, workspace: str = "default", self_correction_rounds: int = 1) -> ResearchTask:
        task_id = str(uuid.uuid4())
        task = ResearchTask(task_id, topic, workspace, self_correction_rounds=self_correction_rounds)
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> ResearchTask:
        return self.tasks.get(task_id)

    async def run_task(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return

        task.status = "RUNNING"
        start_time = time.time()

        def status_callback(orch: AgentOrchestrator):
            # Sync logs from orchestrator
            if orch.logs and len(orch.logs) > len(task.logs):
                for new_log in orch.logs[len(task.logs):]:
                    task.add_log(new_log)

            # Broadcast step updates
            step_status = {}
            for t_id, t_obj in orch.tasks.items():
                step_status[t_id] = {
                    "name": t_obj.name,
                    "status": t_obj.status,
                    "duration": t_obj.duration,
                    "error": t_obj.error
                }

            event_data = {
                "type": "step_update",
                "task_id": task.task_id,
                "status": orch.pipeline_status,
                "steps": step_status,
                "timestamp": time.time()
            }
            for q in list(task.listeners):
                try:
                    q.put_nowait(event_data)
                except Exception:
                    pass

        try:
            task.add_log(f"Starting research on topic: '{task.topic}'")
            orchestrator = AgentOrchestrator(
                topic=task.topic,
                workspace=task.workspace,
                status_callback=status_callback,
                self_correction_rounds=task.self_correction_rounds
            )
            task.orchestrator = orchestrator
            
            # Execute async pipeline
            await orchestrator.run()

            task.status = orchestrator.pipeline_status
            task.duration = round(time.time() - start_time, 2)
            
            # Extract results - report_generator holds the final markdown report
            final_report = orchestrator.tasks["report_generator"].result if "report_generator" in orchestrator.tasks and orchestrator.tasks["report_generator"].result else None
            
            # Summary comes from self_correction's refined_summary, or direct from summarizer
            corr_task = orchestrator.tasks.get("self_correction")
            summary = None
            if corr_task and corr_task.result and isinstance(corr_task.result, dict):
                summary = corr_task.result.get("refined_summary")
            if not summary and "summarizer" in orchestrator.tasks and orchestrator.tasks["summarizer"].result:
                summary = orchestrator.tasks["summarizer"].result

            # Critique comes from self_correction's final_critique, or direct from critic
            critique = None
            if corr_task and corr_task.result and isinstance(corr_task.result, dict):
                critique = corr_task.result.get("final_critique")
            if not critique and "critic" in orchestrator.tasks and orchestrator.tasks["critic"].result:
                critique = orchestrator.tasks["critic"].result

            task.result = {
                "final_report": final_report,
                "summary": summary,
                "critique": critique,
                "pipeline_status": orchestrator.pipeline_status,
                "tasks": {
                    t_id: {
                        "name": t_obj.name,
                        "status": t_obj.status,
                        "duration": t_obj.duration,
                        "error": t_obj.error
                    }
                    for t_id, t_obj in orchestrator.tasks.items()
                }
            }

            task.add_log(f"Pipeline finished with status: {task.status} in {task.duration}s")
            
            # Final event
            final_event = {
                "type": "complete",
                "task_id": task.task_id,
                "status": task.status,
                "result": task.result,
                "timestamp": time.time()
            }
            for q in list(task.listeners):
                try:
                    q.put_nowait(final_event)
                except Exception:
                    pass

        except Exception as e:
            task.status = "FAILED"
            task.duration = round(time.time() - start_time, 2)
            task.add_log(f"Fatal error in pipeline: {str(e)}")
            error_event = {
                "type": "error",
                "task_id": task.task_id,
                "status": "FAILED",
                "error": str(e),
                "timestamp": time.time()
            }
            for q in list(task.listeners):
                try:
                    q.put_nowait(error_event)
                except Exception:
                    pass

    async def stream_task_events(self, task_id: str) -> AsyncGenerator[str, None]:
        task = self.get_task(task_id)
        if not task:
            yield f"data: {{\"error\": \"Task not found\"}}\n\n"
            return

        q = asyncio.Queue()
        task.listeners.append(q)

        # Send initial snapshot
        step_status = {}
        if task.orchestrator:
            for t_id, t_obj in task.orchestrator.tasks.items():
                step_status[t_id] = {
                    "name": t_obj.name,
                    "status": t_obj.status,
                    "duration": t_obj.duration,
                    "error": t_obj.error
                }

        initial_snapshot = {
            "type": "init",
            "task_id": task.task_id,
            "status": task.status,
            "topic": task.topic,
            "logs": task.logs,
            "steps": step_status,
            "result": task.result if task.status in ["COMPLETED", "FAILED"] else None
        }

        import json
        yield f"data: {json.dumps(initial_snapshot)}\n\n"

        try:
            while True:
                # Wait for next event
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ["complete", "error"]:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if q in task.listeners:
                task.listeners.remove(q)

research_service = ResearchService()
