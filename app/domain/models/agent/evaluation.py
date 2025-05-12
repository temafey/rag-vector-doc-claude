"""
Evaluation models for self-assessment in RAG system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import datetime
import uuid

@dataclass
class CriterionScore:
    """Value object for an evaluation criterion score."""
    criterion: str
    score: float  # 0.0 to 1.0
    reason: str
    
    def is_above_threshold(self, threshold: float) -> bool:
        """Check if score is above threshold."""
        return self.score >= threshold

@dataclass
class ResponseEvaluation:
    """Entity representing an evaluation of a generated response."""
    id: str
    agent_id: str
    response_id: str
    query: str
    response: str
    context: List[str]
    scores: Dict[str, CriterionScore]
    overall_score: float
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    @classmethod
    def create(cls, agent_id: str, response_id: str, query: str, 
              response: str, context: List[str]) -> 'ResponseEvaluation':
        """Factory method to create a new response evaluation."""
        return cls(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            response_id=response_id,
            query=query,
            response=response,
            context=context,
            scores={},
            overall_score=0.0
        )
    
    def add_criterion_score(self, criterion: str, score: float, reason: str) -> None:
        """Add score for an evaluation criterion."""
        self.scores[criterion] = CriterionScore(criterion=criterion, score=score, reason=reason)
    
    def calculate_overall_score(self, weights: Dict[str, float] = None) -> float:
        """Calculate overall score as weighted average of criterion scores."""
        if not self.scores:
            return 0.0
        
        # Use equal weights if not specified
        if not weights:
            weights = {criterion: 1.0 for criterion in self.scores}
        
        # Calculate weighted average
        total_weight = sum(weights.get(criterion, 0.0) for criterion in self.scores)
        if total_weight == 0.0:
            return 0.0
        
        weighted_sum = sum(
            score.score * weights.get(score.criterion, 0.0)
            for score in self.scores.values()
        )
        
        self.overall_score = weighted_sum / total_weight
        return self.overall_score
    
    def needs_improvement(self, thresholds: Dict[str, float], 
                          overall_threshold: float) -> bool:
        """Check if response needs improvement based on thresholds."""
        # Check overall score
        if self.overall_score < overall_threshold:
            return True
        
        # Check individual criterion scores
        for criterion, threshold in thresholds.items():
            if criterion in self.scores and self.scores[criterion].score < threshold:
                return True
        
        return False
    
    def get_failing_criteria(self, thresholds: Dict[str, float]) -> List[str]:
        """Get list of criteria that fail to meet thresholds."""
        failing = []
        for criterion, threshold in thresholds.items():
            if criterion in self.scores and self.scores[criterion].score < threshold:
                failing.append(criterion)
        return failing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation to dictionary for serialization."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "response_id": self.response_id,
            "query": self.query,
            "response": self.response,
            "context": self.context,
            "scores": {
                criterion: {
                    "criterion": score.criterion,
                    "score": score.score,
                    "reason": score.reason
                }
                for criterion, score in self.scores.items()
            },
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResponseEvaluation':
        """Create evaluation from dictionary after deserialization."""
        evaluation = cls(
            id=data["id"],
            agent_id=data["agent_id"],
            response_id=data["response_id"],
            query=data["query"],
            response=data["response"],
            context=data["context"],
            scores={},
            overall_score=data["overall_score"],
            created_at=datetime.datetime.fromisoformat(data["created_at"])
        )
        
        # Recreate scores
        for criterion, score_data in data["scores"].items():
            evaluation.scores[criterion] = CriterionScore(
                criterion=score_data["criterion"],
                score=score_data["score"],
                reason=score_data["reason"]
            )
        
        return evaluation

@dataclass
class ImprovementSuggestion:
    """Value object for a suggestion to improve a response."""
    criterion: str
    suggestion: str
    priority: int  # 1-10, higher is more important

@dataclass
class ResponseImprovement:
    """Entity representing an improvement attempt for a response."""
    id: str
    evaluation_id: str
    original_response: str
    improved_response: str
    suggestions: List[ImprovementSuggestion]
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    @classmethod
    def create(cls, evaluation_id: str, original_response: str, 
              improved_response: str, suggestions: List[ImprovementSuggestion]) -> 'ResponseImprovement':
        """Factory method to create a new response improvement."""
        return cls(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation_id,
            original_response=original_response,
            improved_response=improved_response,
            suggestions=suggestions
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert improvement to dictionary for serialization."""
        return {
            "id": self.id,
            "evaluation_id": self.evaluation_id,
            "original_response": self.original_response,
            "improved_response": self.improved_response,
            "suggestions": [
                {
                    "criterion": suggestion.criterion,
                    "suggestion": suggestion.suggestion,
                    "priority": suggestion.priority
                }
                for suggestion in self.suggestions
            ],
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResponseImprovement':
        """Create improvement from dictionary after deserialization."""
        suggestions = [
            ImprovementSuggestion(
                criterion=suggestion_data["criterion"],
                suggestion=suggestion_data["suggestion"],
                priority=suggestion_data["priority"]
            )
            for suggestion_data in data["suggestions"]
        ]
        
        return cls(
            id=data["id"],
            evaluation_id=data["evaluation_id"],
            original_response=data["original_response"],
            improved_response=data["improved_response"],
            suggestions=suggestions,
            created_at=datetime.datetime.fromisoformat(data["created_at"])
        )
