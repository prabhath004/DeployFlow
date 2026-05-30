"""Deployment status state machine.

The single source of truth for which status transitions are legal.
Service code MUST call `transition()` instead of assigning to
deployment.status directly. Routes and the worker both go through here.

PRD §13 reference flows:
  Happy:  QUEUED -> RUNNING -> BUILDING -> [PUSHING_IMAGE ->] DEPLOYING -> SUCCEEDED
  Fail:   any active step -> FAILED -> RETRYING -> QUEUED
  Cancel: QUEUED|RUNNING|BUILDING|... -> CANCELLED
"""

from app.models.enums import DeploymentStatus

S = DeploymentStatus

_ALLOWED: dict[DeploymentStatus, frozenset[DeploymentStatus]] = {
    S.PENDING:       frozenset({S.QUEUED, S.CANCELLED}),
    S.QUEUED:        frozenset({S.RUNNING, S.CANCELLED}),
    S.RUNNING:       frozenset({S.BUILDING, S.FAILED, S.CANCELLED}),
    S.BUILDING:      frozenset({S.PUSHING_IMAGE, S.DEPLOYING, S.FAILED, S.CANCELLED}),
    S.PUSHING_IMAGE: frozenset({S.DEPLOYING, S.FAILED, S.CANCELLED}),
    S.DEPLOYING:     frozenset({S.SUCCEEDED, S.FAILED, S.CANCELLED}),
    S.SUCCEEDED:     frozenset(),  # terminal
    S.FAILED:        frozenset({S.RETRYING}),
    S.CANCELLED:     frozenset(),  # terminal
    S.RETRYING:      frozenset({S.QUEUED}),
}

TERMINAL: frozenset[DeploymentStatus] = frozenset({S.SUCCEEDED, S.CANCELLED})


class InvalidStateTransitionError(Exception):
    def __init__(self, frm: DeploymentStatus, to: DeploymentStatus) -> None:
        super().__init__(f"Illegal deployment transition: {frm} -> {to}")
        self.frm = frm
        self.to = to


def can_transition(frm: DeploymentStatus, to: DeploymentStatus) -> bool:
    return to in _ALLOWED.get(frm, frozenset())


def assert_transition(frm: DeploymentStatus, to: DeploymentStatus) -> None:
    if not can_transition(frm, to):
        raise InvalidStateTransitionError(frm, to)
