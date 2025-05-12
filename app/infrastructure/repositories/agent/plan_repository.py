"""
Repository for plan storage and retrieval.
"""
from typing import Dict, Optional, List
import json
import os
from app.domain.models.agent import Plan

class PlanRepository:
    """Repository for working with plans."""
    
    def __init__(self, storage_path: str):
        """
        Initialize repository.
        
        Args:
            storage_path: Path to directory for plan storage
        """
        self.plans_path = os.path.join(storage_path, "plans")
        os.makedirs(self.plans_path, exist_ok=True)
    
    def _get_plan_path(self, plan_id: str) -> str:
        """Get path to plan file."""
        return os.path.join(self.plans_path, f"{plan_id}.json")
    
    def save(self, plan: Plan) -> None:
        """
        Save plan.
        
        Args:
            plan: Plan to save
        """
        # Create plans directory if it doesn't exist
        os.makedirs(self.plans_path, exist_ok=True)
        
        # Convert plan to dict
        plan_dict = plan.to_dict()
        
        # Save plan to file
        plan_path = self._get_plan_path(plan.id)
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, ensure_ascii=False, indent=2)
    
    def get_by_id(self, plan_id: str) -> Optional[Plan]:
        """
        Get plan by ID.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Plan or None if plan not found
        """
        plan_path = self._get_plan_path(plan_id)
        
        # Check if file exists
        if not os.path.exists(plan_path):
            return None
        
        # Load plan from file
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_dict = json.load(f)
        
        # Create Plan
        plan = Plan.from_dict(plan_dict)
        
        return plan
    
    def delete(self, plan_id: str) -> None:
        """
        Delete plan.
        
        Args:
            plan_id: Plan ID
        """
        plan_path = self._get_plan_path(plan_id)
        
        # Check if file exists
        if os.path.exists(plan_path):
            os.remove(plan_path)
    
    def list_all(self) -> List[Plan]:
        """
        Get list of all plans.
        
        Returns:
            List of plans
        """
        plans = []
        
        # Check if plans directory exists
        if not os.path.exists(self.plans_path):
            return plans
        
        # Iterate through all files in plans directory
        for filename in os.listdir(self.plans_path):
            if filename.endswith(".json"):
                plan_id = filename[:-5]  # Remove .json extension
                plan = self.get_by_id(plan_id)
                if plan:
                    plans.append(plan)
        
        return plans
    
    def list_by_agent_id(self, agent_id: str) -> List[Plan]:
        """
        Get list of plans for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of plans
        """
        # Get all plans
        all_plans = self.list_all()
        
        # Filter plans by agent ID
        return [plan for plan in all_plans if plan.agent_id == agent_id]
