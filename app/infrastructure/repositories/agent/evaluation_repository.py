"""
Repository for evaluation storage and retrieval.
"""
from typing import Dict, Optional, List
import json
import os
from app.domain.models.agent import ResponseEvaluation, ResponseImprovement

class EvaluationRepository:
    """Repository for working with evaluations and improvements."""
    
    def __init__(self, storage_path: str):
        """
        Initialize repository.
        
        Args:
            storage_path: Path to directory for evaluation storage
        """
        self.evaluations_path = os.path.join(storage_path, "evaluations")
        self.improvements_path = os.path.join(storage_path, "improvements")
        os.makedirs(self.evaluations_path, exist_ok=True)
        os.makedirs(self.improvements_path, exist_ok=True)
    
    def _get_evaluation_path(self, evaluation_id: str) -> str:
        """Get path to evaluation file."""
        return os.path.join(self.evaluations_path, f"{evaluation_id}.json")
    
    def _get_improvement_path(self, improvement_id: str) -> str:
        """Get path to improvement file."""
        return os.path.join(self.improvements_path, f"{improvement_id}.json")
    
    def save_evaluation(self, evaluation: ResponseEvaluation) -> None:
        """
        Save evaluation.
        
        Args:
            evaluation: Evaluation to save
        """
        # Create evaluations directory if it doesn't exist
        os.makedirs(self.evaluations_path, exist_ok=True)
        
        # Convert evaluation to dict
        evaluation_dict = evaluation.to_dict()
        
        # Save evaluation to file
        evaluation_path = self._get_evaluation_path(evaluation.id)
        with open(evaluation_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_dict, f, ensure_ascii=False, indent=2)
    
    def get_evaluation_by_id(self, evaluation_id: str) -> Optional[ResponseEvaluation]:
        """
        Get evaluation by ID.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Evaluation or None if evaluation not found
        """
        evaluation_path = self._get_evaluation_path(evaluation_id)
        
        # Check if file exists
        if not os.path.exists(evaluation_path):
            return None
        
        # Load evaluation from file
        with open(evaluation_path, "r", encoding="utf-8") as f:
            evaluation_dict = json.load(f)
        
        # Create Evaluation
        evaluation = ResponseEvaluation.from_dict(evaluation_dict)
        
        return evaluation
    
    def save_improvement(self, improvement: ResponseImprovement) -> None:
        """
        Save improvement.
        
        Args:
            improvement: Improvement to save
        """
        # Create improvements directory if it doesn't exist
        os.makedirs(self.improvements_path, exist_ok=True)
        
        # Convert improvement to dict
        improvement_dict = improvement.to_dict()
        
        # Save improvement to file
        improvement_path = self._get_improvement_path(improvement.id)
        with open(improvement_path, "w", encoding="utf-8") as f:
            json.dump(improvement_dict, f, ensure_ascii=False, indent=2)
    
    def get_improvement_by_id(self, improvement_id: str) -> Optional[ResponseImprovement]:
        """
        Get improvement by ID.
        
        Args:
            improvement_id: Improvement ID
            
        Returns:
            Improvement or None if improvement not found
        """
        improvement_path = self._get_improvement_path(improvement_id)
        
        # Check if file exists
        if not os.path.exists(improvement_path):
            return None
        
        # Load improvement from file
        with open(improvement_path, "r", encoding="utf-8") as f:
            improvement_dict = json.load(f)
        
        # Create Improvement
        improvement = ResponseImprovement.from_dict(improvement_dict)
        
        return improvement
    
    def delete_evaluation(self, evaluation_id: str) -> None:
        """
        Delete evaluation.
        
        Args:
            evaluation_id: Evaluation ID
        """
        evaluation_path = self._get_evaluation_path(evaluation_id)
        
        # Check if file exists
        if os.path.exists(evaluation_path):
            os.remove(evaluation_path)
    
    def delete_improvement(self, improvement_id: str) -> None:
        """
        Delete improvement.
        
        Args:
            improvement_id: Improvement ID
        """
        improvement_path = self._get_improvement_path(improvement_id)
        
        # Check if file exists
        if os.path.exists(improvement_path):
            os.remove(improvement_path)
    
    def list_evaluations(self, agent_id: Optional[str] = None) -> List[ResponseEvaluation]:
        """
        Get list of evaluations.
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            List of evaluations
        """
        evaluations = []
        
        # Check if evaluations directory exists
        if not os.path.exists(self.evaluations_path):
            return evaluations
        
        # Iterate through all files in evaluations directory
        for filename in os.listdir(self.evaluations_path):
            if filename.endswith(".json"):
                evaluation_id = filename[:-5]  # Remove .json extension
                evaluation = self.get_evaluation_by_id(evaluation_id)
                if evaluation and (agent_id is None or evaluation.agent_id == agent_id):
                    evaluations.append(evaluation)
        
        return evaluations
    
    def list_improvements(self, evaluation_id: Optional[str] = None) -> List[ResponseImprovement]:
        """
        Get list of improvements.
        
        Args:
            evaluation_id: Optional evaluation ID to filter by
            
        Returns:
            List of improvements
        """
        improvements = []
        
        # Check if improvements directory exists
        if not os.path.exists(self.improvements_path):
            return improvements
        
        # Iterate through all files in improvements directory
        for filename in os.listdir(self.improvements_path):
            if filename.endswith(".json"):
                improvement_id = filename[:-5]  # Remove .json extension
                improvement = self.get_improvement_by_id(improvement_id)
                if improvement and (evaluation_id is None or improvement.evaluation_id == evaluation_id):
                    improvements.append(improvement)
        
        return improvements
    
    def get_improvement_by_evaluation_id(self, evaluation_id: str) -> Optional[ResponseImprovement]:
        """
        Get improvement by evaluation ID.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Improvement or None if no improvement found for evaluation
        """
        # Get all improvements
        improvements = self.list_improvements(evaluation_id)
        
        # Return first improvement (there should only be one per evaluation)
        return improvements[0] if improvements else None
