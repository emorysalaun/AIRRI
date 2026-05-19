"""adversarial.pipeline — Core pipeline orchestration."""

from .runner import AdversarialPipeline
from .dispatcher import dispatch_attack
from .reporter import PipelineReporter

__all__ = ["AdversarialPipeline", "dispatch_attack", "PipelineReporter"]
