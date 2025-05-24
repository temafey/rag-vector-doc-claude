"""
Evaluation service for self-assessment in RAG system.
"""
from typing import Dict, List, Any, Optional
from app.domain.models.agent import (
    Agent, ResponseEvaluation, CriterionScore, 
    ImprovementSuggestion, ResponseImprovement
)
from app.infrastructure.event_bus import event_bus
from app.domain.events.agent_events import (
    ResponseEvaluatedEvent,
    ResponseImprovedEvent
)
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import json
import uuid

class EvaluationService:
    """Service for evaluating responses."""
    
    def __init__(self, llm_client=None):
        # Initialize LLM for evaluation
        if llm_client:
            self.llm = llm_client
        else:
            from app.config.config_loader import get_config
            config = get_config()
            self.llm = ChatOpenAI(
                openai_api_key=config["langchain"].get("api_key"),
                model_name=config["langchain"].get("llm_model", "gpt-3.5-turbo")
            )
        
        # Create evaluation prompt templates
        self.evaluation_templates = {
            "relevance": PromptTemplate(
                input_variables=["query", "response"],
                template="""Evaluate how relevant the following response is to the query.

Query: {query}

Response: {response}

Score the relevance on a scale of 0.0 to 1.0, where:
0.0 = Completely irrelevant, does not address the query at all
0.5 = Partially relevant, addresses some aspects of the query but misses key points
1.0 = Highly relevant, directly and comprehensively addresses the query

Provide your evaluation in the following JSON format:
```json
{{
  "score": 0.8,
  "reason": "The response is highly relevant because..."
}}
```
"""
            ),
            "factual_accuracy": PromptTemplate(
                input_variables=["response", "context"],
                template="""Evaluate the factual accuracy of the following response based on the provided context.

Context:
{context}

Response: {response}

Score the factual accuracy on a scale of 0.0 to 1.0, where:
0.0 = Contains major factual errors or contradictions with the context
0.5 = Contains minor inaccuracies or omissions
1.0 = Completely factually accurate, all statements are supported by the context

Provide your evaluation in the following JSON format:
```json
{{
  "score": 0.8,
  "reason": "The response is factually accurate because..."
}}
```
"""
            ),
            "completeness": PromptTemplate(
                input_variables=["query", "response"],
                template="""Evaluate how complete the following response is in addressing the query.

Query: {query}

Response: {response}

Score the completeness on a scale of 0.0 to 1.0, where:
0.0 = Extremely incomplete, fails to address most aspects of the query
0.5 = Moderately complete, addresses main points but leaves out some details
1.0 = Fully complete, addresses all aspects of the query comprehensively

Provide your evaluation in the following JSON format:
```json
{{
  "score": 0.8,
  "reason": "The response is complete because..."
}}
```
"""
            ),
            "logical_coherence": PromptTemplate(
                input_variables=["response"],
                template="""Evaluate the logical coherence and structure of the following response.

Response: {response}

Score the logical coherence on a scale of 0.0 to 1.0, where:
0.0 = Incoherent, disorganized, with major logical flaws or contradictions
0.5 = Somewhat coherent, but with some structural issues or minor logical problems
1.0 = Perfectly coherent, well-structured, logically sound throughout

Provide your evaluation in the following JSON format:
```json
{{
  "score": 0.8,
  "reason": "The response is coherent because..."
}}
```
"""
            ),
            "ethical_compliance": PromptTemplate(
                input_variables=["response"],
                template="""Evaluate the ethical compliance of the following response.

Response: {response}

Score the ethical compliance on a scale of 0.0 to 1.0, where:
0.0 = Contains harmful content, misinformation, or violates ethical principles
0.5 = Contains potentially problematic content but not overtly harmful
1.0 = Fully compliant with ethical guidelines, no harmful or problematic content

Provide your evaluation in the following JSON format:
```json
{{
  "score": 0.8,
  "reason": "The response is ethically compliant because..."
}}
```
"""
            )
        }
        
        # Create improvement prompt template
        self.improvement_template = PromptTemplate(
            input_variables=["query", "response", "context", "evaluation"],
            template="""Improve the following response based on the evaluation feedback.

Query: {query}

Original Response: {response}

Context:
{context}

Evaluation:
{evaluation}

Your task is to improve the response by addressing the issues identified in the evaluation.
Focus on fixing problems with relevance, factual accuracy, completeness, logical coherence, and ethical compliance.

First, provide specific improvement suggestions in the following JSON format:
```json
{{
  "suggestions": [
    {{
      "criterion": "relevance",
      "suggestion": "Focus more directly on answering the specific question asked",
      "priority": 8
    }},
    ...
  ]
}}
```

Then, provide an improved version of the response that addresses these suggestions.
"""
        )
        
        # Create LLM chains
        self.evaluation_chains = {}
        for criterion, template in self.evaluation_templates.items():
            self.evaluation_chains[criterion] = template | self.llm
        
        self.improvement_chain = self.improvement_template | self.llm
        
        # Default quality thresholds and weights
        self.quality_thresholds = {
            "relevance": 0.7,
            "factual_accuracy": 0.8,
            "completeness": 0.7,
            "logical_coherence": 0.7,
            "ethical_compliance": 0.9
        }
        
        self.criterion_weights = {
            "relevance": 0.25,
            "factual_accuracy": 0.3,
            "completeness": 0.2,
            "logical_coherence": 0.15,
            "ethical_compliance": 0.1
        }
        
        self.overall_threshold = 0.75
    
    def evaluate_response(self, agent: Agent, query: str, response: str, 
                         context: List[str]) -> ResponseEvaluation:
        """Evaluate response quality based on defined criteria."""
        # Create response ID if not provided
        response_id = str(uuid.uuid4())
        
        # Create evaluation
        evaluation = ResponseEvaluation.create(
            agent_id=agent.id,
            response_id=response_id,
            query=query,
            response=response,
            context=context
        )
        
        # Format context as string for evaluation
        context_str = "\n\n".join(context)
        
        # Evaluate each criterion
        for criterion, chain in self.evaluation_chains.items():
            if criterion == "relevance":
                result = chain.run(query=query, response=response)
            elif criterion == "factual_accuracy":
                result = chain.run(response=response, context=context_str)
            elif criterion == "completeness":
                result = chain.run(query=query, response=response)
            elif criterion == "logical_coherence":
                result = chain.run(response=response)
            elif criterion == "ethical_compliance":
                result = chain.run(response=response)
            
            # Extract JSON from result
            try:
                # Find JSON block in response
                json_start = result.find("```json") + 7 if "```json" in result else 0
                json_end = result.find("```", json_start) if "```" in result[json_start:] else len(result)
                json_str = result[json_start:json_end].strip()
                
                # Parse JSON
                eval_data = json.loads(json_str)
                
                # Add criterion score
                evaluation.add_criterion_score(
                    criterion=criterion,
                    score=float(eval_data.get("score", 0.0)),
                    reason=eval_data.get("reason", "")
                )
            except Exception as e:
                # Fallback for when JSON extraction fails
                evaluation.add_criterion_score(
                    criterion=criterion,
                    score=0.5,  # Default to middle score
                    reason=f"Failed to parse evaluation: {str(e)}"
                )
        
        # Calculate overall score
        evaluation.calculate_overall_score(self.criterion_weights)
        
        # Determine if improvement is needed
        needs_improvement = evaluation.needs_improvement(self.quality_thresholds, self.overall_threshold)
        
        # Store evaluation in agent memory
        agent.state.set_memory("last_evaluation", evaluation.id)
        
        # Publish response evaluated event
        event_bus.publish(ResponseEvaluatedEvent(
            agent_id=agent.id,
            evaluation_id=evaluation.id,
            response_id=response_id,
            overall_score=evaluation.overall_score,
            needs_improvement=needs_improvement
        ))
        
        return evaluation
    
    def improve_response(self, agent: Agent, evaluation: ResponseEvaluation) -> ResponseImprovement:
        """Improve response based on evaluation."""
        # Format context as string
        context_str = "\n\n".join(evaluation.context)
        
        # Format evaluation as string
        evaluation_str = "\n".join([
            f"{criterion}: {score.score:.2f} - {score.reason}"
            for criterion, score in evaluation.scores.items()
        ])
        
        # Generate improvement
        improvement_result = self.improvement_chain.run(
            query=evaluation.query,
            response=evaluation.response,
            context=context_str,
            evaluation=evaluation_str
        )
        
        # Extract suggestions JSON
        try:
            # Find JSON block in response
            json_start = improvement_result.find("```json") + 7 if "```json" in improvement_result else 0
            json_end = improvement_result.find("```", json_start) if "```" in improvement_result[json_start:] else len(improvement_result)
            json_str = improvement_result[json_start:json_end].strip()
            
            # Parse JSON
            suggestions_data = json.loads(json_str)
            
            # Create suggestion objects
            suggestions = []
            for suggestion_data in suggestions_data.get("suggestions", []):
                suggestions.append(ImprovementSuggestion(
                    criterion=suggestion_data.get("criterion", ""),
                    suggestion=suggestion_data.get("suggestion", ""),
                    priority=int(suggestion_data.get("priority", 5))
                ))
        except Exception:
            # Fallback for when JSON extraction fails
            suggestions = [
                ImprovementSuggestion(
                    criterion="general",
                    suggestion="Improve the response based on evaluation feedback",
                    priority=5
                )
            ]
        
        # Extract improved response (everything after the JSON block)
        improved_response = improvement_result[json_end:].strip()
        if improved_response.startswith("```"):
            improved_response = improved_response[improved_response.find("\n")+1:].strip()
        if improved_response.endswith("```"):
            improved_response = improved_response[:improved_response.rfind("```")].strip()
        
        # Create improvement
        improvement = ResponseImprovement.create(
            evaluation_id=evaluation.id,
            original_response=evaluation.response,
            improved_response=improved_response,
            suggestions=suggestions
        )
        
        # Store improvement in agent memory
        agent.state.set_memory("last_improvement", improvement.id)
        
        # Publish response improved event
        event_bus.publish(ResponseImprovedEvent(
            agent_id=agent.id,
            evaluation_id=evaluation.id,
            improvement_id=improvement.id,
            original_response=evaluation.response,
            improved_response=improved_response
        ))
        
        return improvement
    
    def evaluate_and_improve(self, agent: Agent, query: str, response: str, 
                            context: List[str]) -> Dict[str, Any]:
        """
        Evaluate response and improve if necessary.
        
        This is the main entry point for self-assessment.
        """
        # Evaluate response
        evaluation = self.evaluate_response(agent, query, response, context)
        
        # Determine if improvement is needed
        needs_improvement = evaluation.needs_improvement(
            self.quality_thresholds, 
            self.overall_threshold
        )
        
        # If improvement is needed, improve response
        if needs_improvement:
            improvement = self.improve_response(agent, evaluation)
            
            # Return result with improved response
            return {
                "original_response": response,
                "improved_response": improvement.improved_response,
                "evaluation": {
                    "id": evaluation.id,
                    "overall_score": evaluation.overall_score,
                    "criterion_scores": {
                        criterion: {
                            "score": score.score,
                            "reason": score.reason
                        }
                        for criterion, score in evaluation.scores.items()
                    }
                },
                "suggestions": [
                    {
                        "criterion": suggestion.criterion,
                        "suggestion": suggestion.suggestion,
                        "priority": suggestion.priority
                    }
                    for suggestion in improvement.suggestions
                ],
                "improved": True
            }
        
        # If no improvement is needed, return original response
        return {
            "response": response,
            "evaluation": {
                "id": evaluation.id,
                "overall_score": evaluation.overall_score,
                "criterion_scores": {
                    criterion: {
                        "score": score.score,
                        "reason": score.reason
                    }
                    for criterion, score in evaluation.scores.items()
                }
            },
            "improved": False
        }
    
    def set_quality_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set quality thresholds for evaluation criteria."""
        self.quality_thresholds.update(thresholds)
    
    def set_criterion_weights(self, weights: Dict[str, float]) -> None:
        """Set weights for evaluation criteria."""
        self.criterion_weights.update(weights)
    
    def set_overall_threshold(self, threshold: float) -> None:
        """Set overall quality threshold."""
        self.overall_threshold = threshold
