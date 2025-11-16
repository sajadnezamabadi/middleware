from __future__ import annotations

import random
from typing import Any

from django.dispatch import Signal, receiver

# allowed, reason, user_id, application, method, path, matched_route_id, sampling_rate
access_checked = Signal()


@receiver(access_checked)
def _sampled_logger(sender, **kwargs: Any):
    sampling_rate: float = float(kwargs.get("sampling_rate", 1.0) or 1.0)
    if sampling_rate <= 0:
        return
    if sampling_rate < 1.0 and random.random() > sampling_rate:
        return
    # no logging sink by default; projects can connect their own receivers
    # this default receiver is a no-op (kept for future extension)
    return


