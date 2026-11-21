"""Pending clarify/approval prompts must survive resume snapshots.

``session.resume``/``session.activate`` attach computes the snapshot generation
from the execution state: idle/waiting/unknown yields ``None``. Pruning a
still-pending prompt on a generation mismatch wiped the parked clarify/approval
card when the viewer returned to the session (the desktop treats a snapshot
without the prompt as authoritative-absent and clears the card), while the
agent kept blocking on the human. Only inactive (settled) prompts may be
pruned.
"""
from __future__ import annotations

import threading

from gateway.session_pending_controls import PendingControls


class _FakeEvents:
    def __init__(self):
        self.lock = threading.RLock()
        self.published = []

    def publish(self, sid, payload, event_type=None):
        self.published.append((event_type, payload))


class _FakeEntry:
    def __init__(self, cid):
        self.clarify_id = cid
        self.question = 'Ship it?'
        self.choices = ['yes', 'no']
        self.multi_select = False
        self.event = threading.Event()


def _fresh():
    events = _FakeEvents()
    controls = PendingControls(events)
    entry = _FakeEntry('clar-1')
    controls.register_clarify('sess-1', 5, entry)
    return controls, entry


def _ids(controls, generation):
    return [p['prompt_id'] for p in controls.snapshot('sess-1', generation)]


def test_pending_survives_snapshot_without_generation():
    controls, _ = _fresh()
    assert _ids(controls, None) == ['clar-1']


def test_pending_survives_mismatched_generation():
    controls, _ = _fresh()
    assert _ids(controls, 6) == ['clar-1']


def test_pending_survives_matching_generation():
    controls, _ = _fresh()
    assert _ids(controls, 5) == ['clar-1']


def test_settled_clarify_is_still_pruned():
    controls, entry = _fresh()
    entry.event.set()
    assert _ids(controls, 5) == []


def test_pending_survives_repeated_resumes():
    controls, _ = _fresh()
    for generation in (None, 5, 6, None):
        controls.snapshot('sess-1', generation)
    assert _ids(controls, None) == ['clar-1']
