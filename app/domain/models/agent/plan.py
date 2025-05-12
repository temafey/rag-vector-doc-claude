"""
Plan model for agent planning in RAG system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import datetime
import uuid

@dataclass
class PlanStep:
    """Value object representing a step in a plan."""
    id: str
    step_number: int
    action_type: str
    description: str
    parameters: Dict[str, Any]
    dependencies: List[int] = field(default_factory=list)
    status: str = "pending"  # pending, in-progress, completed, failed, skipped
    result: Optional[Any] = None
    
    @classmethod
    def create(cls, step_number: int, action_type: str, description: str, 
              parameters: Dict[str, Any], dependencies: List[int] = None) -> 'PlanStep':
        """Factory method to create a new plan step."""
        return cls(
            id=str(uuid.uuid4()),
            step_number=step_number,
            action_type=action_type,
            description=description,
            parameters=parameters,
            dependencies=dependencies or []
        )
    
    def update_status(self, status: str, result: Any = None) -> None:
        """Update step status and result."""
        self.status = status
        if result is not None:
            self.result = result
    
    def is_ready(self, completed_steps: List[int]) -> bool:
        """Check if step is ready to be executed (all dependencies completed)."""
        for dep in self.dependencies:
            if dep not in completed_steps:
                return False
        return True

@dataclass
class Plan:
    """Entity representing a plan for solving a task."""
    id: str
    agent_id: str
    task: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    status: str = "created"  # created, in-progress, completed, failed
    
    @classmethod
    def create(cls, agent_id: str, task: str) -> 'Plan':
        """Factory method to create a new plan."""
        return cls(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            task=task
        )
    
    def add_step(self, action_type: str, description: str, 
                parameters: Dict[str, Any], dependencies: List[int] = None) -> PlanStep:
        """Add step to plan."""
        step_number = len(self.steps) + 1
        step = PlanStep.create(
            step_number=step_number,
            action_type=action_type,
            description=description,
            parameters=parameters,
            dependencies=dependencies or []
        )
        self.steps.append(step)
        self.updated_at = datetime.datetime.now()
        return step
    
    def get_step(self, step_number: int) -> Optional[PlanStep]:
        """Get step by number."""
        for step in self.steps:
            if step.step_number == step_number:
                return step
        return None
    
    def update_step_status(self, step_number: int, status: str, result: Any = None) -> None:
        """Update step status and result."""
        step = self.get_step(step_number)
        if step:
            step.update_status(status, result)
            self.updated_at = datetime.datetime.now()
            
            # Update plan status if necessary
            if status == "failed":
                self.status = "failed"
            elif self._all_steps_completed():
                self.status = "completed"
    
    def _all_steps_completed(self) -> bool:
        """Check if all steps are completed or skipped."""
        for step in self.steps:
            if step.status not in ["completed", "skipped"]:
                return False
        return True
    
    def get_next_steps(self) -> List[PlanStep]:
        """Get steps that are ready to be executed."""
        completed_steps = [step.step_number for step in self.steps 
                          if step.status in ["completed", "skipped"]]
        
        next_steps = []
        for step in self.steps:
            if (step.status == "pending" and 
                step.is_ready(completed_steps)):
                next_steps.append(step)
        
        return next_steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for serialization."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task": self.task,
            "steps": [
                {
                    "id": step.id,
                    "step_number": step.step_number,
                    "action_type": step.action_type,
                    "description": step.description,
                    "parameters": step.parameters,
                    "dependencies": step.dependencies,
                    "status": step.status,
                    "result": step.result
                }
                for step in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """Create plan from dictionary after deserialization."""
        plan = cls(
            id=data["id"],
            agent_id=data["agent_id"],
            task=data["task"],
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.datetime.fromisoformat(data["updated_at"]),
            status=data["status"]
        )
        
        # Recreate steps
        for step_data in data["steps"]:
            step = PlanStep(
                id=step_data["id"],
                step_number=step_data["step_number"],
                action_type=step_data["action_type"],
                description=step_data["description"],
                parameters=step_data["parameters"],
                dependencies=step_data["dependencies"],
                status=step_data["status"],
                result=step_data["result"]
            )
            plan.steps.append(step)
        
        return plan
