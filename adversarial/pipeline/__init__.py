"""adversarial.pipeline — Core pipeline orchestration."""

from .dispatcher import dispatch_attack
from .reporter import PipelineReporter

__all__ = ["dispatch_attack", "PipelineReporter"]
