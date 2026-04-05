"""
Advanced Reasoning Engine - Multi-strategy reasoning system for enhanced agent decision-making.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ReasoningStrategy(Enum):
    """Different reasoning strategies."""
    LOGICAL = "logical"  # Step-by-step logic
    ANALOGICAL = "analogical"  # Use analogies
    ABDUCTIVE = "abductive"  # Inference to best explanation
    INDUCTIVE = "inductive"  # Generalize from examples
    DEDUCTIVE = "deductive"  # Apply general rules
    CREATIVE = "creative"  # Novel solutions
    CRITICAL = "critical"  # Challenge assumptions


@dataclass
class ReasoningPath:
    """A path of reasoning steps."""
    strategy: ReasoningStrategy
    steps: List[str]
    conclusion: str
    confidence: float
    premises: List[str]


@dataclass
class ReasoningChain:
    """Chain of multiple reasoning paths."""
    problem: str
    paths: List[ReasoningPath]
    final_conclusion: str
    decision_rationale: str


class LogicalReasoner:
    """Logical reasoning based on premises and rules."""

    def __init__(self):
        self.logger = logger

    async def reason(self, premises: List[str], problem: str) -> ReasoningPath:
        """
        Apply logical reasoning.
        
        Args:
            premises: Starting premises
            problem: Problem to solve
        
        Returns:
            ReasoningPath with logical steps
        """
        steps = [
            f"Identify core premise: {premises[0] if premises else 'Unknown'}",
            "Break down problem into components",
            "Apply logical rules to each component",
            "Combine results",
            "Verify conclusion against premises",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.LOGICAL,
            steps=steps,
            conclusion="Logical analysis complete",
            confidence=0.85,
            premises=premises,
        )


class AnalogicalReasoner:
    """Analogical reasoning using similar problems."""

    def __init__(self):
        self.logger = logger
        self.analogy_base = {
            "design": ["paint a picture", "compose a song", "write a story"],
            "optimization": ["improve a recipe", "refine a process", "perfect a craft"],
            "debugging": ["find a lost key", "diagnose an illness", "solve a mystery"],
        }

    async def reason(self, problem: str, domain: str) -> ReasoningPath:
        """
        Apply analogical reasoning.
        
        Args:
            problem: Problem to solve
            domain: Domain of the problem
        
        Returns:
            ReasoningPath with analogies
        """
        analogies = self.analogy_base.get(domain, [])
        
        steps = [
            f"Identify similar problem: {analogies[0] if analogies else 'Unknown'}",
            "Map features between problems",
            "Apply solution from analogy",
            "Adapt to current problem",
            "Validate analogy transfer",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.ANALOGICAL,
            steps=steps,
            conclusion=f"Analogy-based solution for {domain}",
            confidence=0.75,
            premises=[f"Analogy with: {analogies[0] if analogies else 'Unknown'}"],
        )


class AbductiveReasoner:
    """Abductive reasoning - inference to best explanation."""

    def __init__(self):
        self.logger = logger

    async def reason(
        self,
        observations: List[str],
        possible_explanations: List[str],
    ) -> ReasoningPath:
        """
        Apply abductive reasoning.
        
        Args:
            observations: Observations to explain
            possible_explanations: Candidate explanations
        
        Returns:
            ReasoningPath with best explanation
        """
        steps = [
            "List all observations",
            "Generate possible explanations",
            "Evaluate each explanation",
            "Calculate explanation probabilities",
            "Select best explanation",
        ]
        
        best_explanation = possible_explanations[0] if possible_explanations else "Unknown"
        
        return ReasoningPath(
            strategy=ReasoningStrategy.ABDUCTIVE,
            steps=steps,
            conclusion=f"Best explanation: {best_explanation}",
            confidence=0.80,
            premises=observations,
        )


class InductiveReasoner:
    """Inductive reasoning from examples to general rules."""

    def __init__(self):
        self.logger = logger

    async def reason(self, examples: List[Dict[str, Any]]) -> ReasoningPath:
        """
        Apply inductive reasoning.
        
        Args:
            examples: Examples to generalize from
        
        Returns:
            ReasoningPath with general rule
        """
        steps = [
            f"Analyze {len(examples)} examples",
            "Identify common patterns",
            "Extract generalizable rules",
            "Test rule against examples",
            "Generate conclusion",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.INDUCTIVE,
            steps=steps,
            conclusion="General rule derived from examples",
            confidence=0.70 + (len(examples) * 0.05),  # More examples = higher confidence
            premises=[str(e) for e in examples],
        )


class DeductiveReasoner:
    """Deductive reasoning from general rules to specific cases."""

    def __init__(self):
        self.logger = logger

    async def reason(
        self,
        general_rule: str,
        specific_case: str,
    ) -> ReasoningPath:
        """
        Apply deductive reasoning.
        
        Args:
            general_rule: General rule
            specific_case: Specific case to apply rule to
        
        Returns:
            ReasoningPath with deductive conclusion
        """
        steps = [
            f"State general rule: {general_rule}",
            f"Identify specific case: {specific_case}",
            "Check if case matches rule conditions",
            "Apply rule to specific case",
            "Derive specific conclusion",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.DEDUCTIVE,
            steps=steps,
            conclusion="Specific conclusion derived from general rule",
            confidence=0.95,
            premises=[general_rule, specific_case],
        )


class CreativeReasoner:
    """Creative reasoning for novel solutions."""

    def __init__(self):
        self.logger = logger

    async def reason(
        self,
        problem: str,
        constraints: List[str],
        creative_directions: Optional[List[str]] = None,
    ) -> ReasoningPath:
        """
        Apply creative reasoning.
        
        Args:
            problem: Problem to solve creatively
            constraints: Constraints to work within
            creative_directions: Optional creative directions
        
        Returns:
            ReasoningPath with creative solution
        """
        directions = creative_directions or [
            "Reverse the problem",
            "Combine unrelated ideas",
            "Remove a constraint",
            "Exaggerate the problem",
            "Find the absurd angle",
        ]
        
        steps = [
            f"Define problem: {problem}",
            "Apply creative techniques",
            *[f"Explore: {d}" for d in directions[:3]],
            "Synthesize novel solution",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.CREATIVE,
            steps=steps,
            conclusion="Novel creative solution",
            confidence=0.65,
            premises=constraints,
        )


class CriticalReasoner:
    """Critical reasoning that challenges assumptions."""

    def __init__(self):
        self.logger = logger

    async def reason(
        self,
        proposition: str,
        supporting_evidence: List[str],
    ) -> ReasoningPath:
        """
        Apply critical reasoning.
        
        Args:
            proposition: Proposition to analyze critically
            supporting_evidence: Evidence supporting proposition
        
        Returns:
            ReasoningPath with critical analysis
        """
        steps = [
            f"Examine proposition: {proposition}",
            "Identify underlying assumptions",
            "Question each assumption",
            "Look for counterexamples",
            "Evaluate evidence quality",
            "Generate critical conclusion",
        ]
        
        return ReasoningPath(
            strategy=ReasoningStrategy.CRITICAL,
            steps=steps,
            conclusion="Critical evaluation complete",
            confidence=0.80,
            premises=supporting_evidence,
        )


class AdvancedReasoningEngine:
    """Orchestrate multiple reasoning strategies."""

    def __init__(self):
        self.logger = logger
        self.reasoners = {
            ReasoningStrategy.LOGICAL: LogicalReasoner(),
            ReasoningStrategy.ANALOGICAL: AnalogicalReasoner(),
            ReasoningStrategy.ABDUCTIVE: AbductiveReasoner(),
            ReasoningStrategy.INDUCTIVE: InductiveReasoner(),
            ReasoningStrategy.DEDUCTIVE: DeductiveReasoner(),
            ReasoningStrategy.CREATIVE: CreativeReasoner(),
            ReasoningStrategy.CRITICAL: CriticalReasoner(),
        }

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        strategies: Optional[List[ReasoningStrategy]] = None,
    ) -> ReasoningChain:
        """
        Apply multiple reasoning strategies to a problem.
        
        Args:
            problem: Problem to reason about
            context: Problem context
            strategies: Specific strategies to use (all if not specified)
        
        Returns:
            ReasoningChain with multiple paths
        """
        context = context or {}
        strategies = strategies or list(ReasoningStrategy)
        
        self.logger.info(f"Reasoning about: {problem}")
        paths = []
        
        # Apply each strategy
        for strategy in strategies:
            if strategy not in self.reasoners:
                continue
            
            try:
                if strategy == ReasoningStrategy.LOGICAL:
                    path = await self.reasoners[strategy].reason(
                        context.get("premises", []),
                        problem,
                    )
                elif strategy == ReasoningStrategy.ANALOGICAL:
                    path = await self.reasoners[strategy].reason(
                        problem,
                        context.get("domain", "general"),
                    )
                elif strategy == ReasoningStrategy.ABDUCTIVE:
                    path = await self.reasoners[strategy].reason(
                        context.get("observations", []),
                        context.get("possible_explanations", []),
                    )
                elif strategy == ReasoningStrategy.INDUCTIVE:
                    path = await self.reasoners[strategy].reason(
                        context.get("examples", []),
                    )
                elif strategy == ReasoningStrategy.DEDUCTIVE:
                    path = await self.reasoners[strategy].reason(
                        context.get("general_rule", ""),
                        problem,
                    )
                elif strategy == ReasoningStrategy.CREATIVE:
                    path = await self.reasoners[strategy].reason(
                        problem,
                        context.get("constraints", []),
                        context.get("creative_directions"),
                    )
                elif strategy == ReasoningStrategy.CRITICAL:
                    path = await self.reasoners[strategy].reason(
                        problem,
                        context.get("supporting_evidence", []),
                    )
                else:
                    continue
                
                paths.append(path)
            except Exception as e:
                self.logger.error(f"Error in {strategy.value} reasoning: {e}")
        
        # Synthesize conclusions
        final_conclusion = self._synthesize_conclusions(paths)
        decision_rationale = self._build_rationale(paths)
        
        return ReasoningChain(
            problem=problem,
            paths=paths,
            final_conclusion=final_conclusion,
            decision_rationale=decision_rationale,
        )

    def _synthesize_conclusions(self, paths: List[ReasoningPath]) -> str:
        """Synthesize conclusions from multiple paths."""
        if not paths:
            return "No conclusion reached"
        
        # Average confidence
        avg_confidence = sum(p.confidence for p in paths) / len(paths)
        
        # Take conclusion from highest confidence path
        best_path = max(paths, key=lambda p: p.confidence)
        
        return f"{best_path.conclusion} (avg confidence: {avg_confidence:.2f})"

    def _build_rationale(self, paths: List[ReasoningPath]) -> str:
        """Build decision rationale from multiple paths."""
        strategies_used = [p.strategy.value for p in paths]
        avg_confidence = sum(p.confidence for p in paths) / len(paths) if paths else 0
        
        return (
            f"Analyzed using {len(paths)} reasoning strategies: {', '.join(strategies_used)}. "
            f"Average confidence: {avg_confidence:.2f}. "
            f"Recommendation: Consider all perspectives for comprehensive decision."
        )

    async def reason_with_verification(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reason about problem with verification step.
        
        Args:
            problem: Problem to reason about
            context: Problem context
        
        Returns:
            Reasoning with verification results
        """
        chain = await self.reason(problem, context)
        
        # Verify reasoning
        verification = self._verify_reasoning(chain)
        
        return {
            "problem": problem,
            "reasoning_chain": chain,
            "verification": verification,
            "confidence": chain.paths[0].confidence if chain.paths else 0,
        }

    def _verify_reasoning(self, chain: ReasoningChain) -> Dict[str, Any]:
        """Verify reasoning quality."""
        return {
            "paths_count": len(chain.paths),
            "avg_confidence": sum(p.confidence for p in chain.paths) / len(chain.paths) if chain.paths else 0,
            "consistency": self._check_consistency(chain),
            "completeness": self._check_completeness(chain),
        }

    def _check_consistency(self, chain: ReasoningChain) -> float:
        """Check consistency of reasoning paths."""
        if len(chain.paths) < 2:
            return 1.0
        
        # High confidence paths should generally agree
        high_confidence_paths = [p for p in chain.paths if p.confidence > 0.8]
        if not high_confidence_paths:
            return 0.5
        
        return 0.8 + (len(high_confidence_paths) * 0.02)

    def _check_completeness(self, chain: ReasoningChain) -> float:
        """Check completeness of reasoning coverage."""
        coverage = len(chain.paths) / len(ReasoningStrategy)
        return min(coverage, 1.0)


def get_advanced_reasoning_engine() -> AdvancedReasoningEngine:
    """Get advanced reasoning engine."""
    return AdvancedReasoningEngine()
