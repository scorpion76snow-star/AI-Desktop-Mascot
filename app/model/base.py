# -*- coding: utf-8 -*-
"""Model backend interface."""


class ModelBackend:
    name = "base"

    def load(self):
        return self

    def unload(self):
        return None

    def status(self):
        return {"loaded": False, "device": "", "model": self.name}

    def reply_messages(self, system, turns, max_new=120):
        raise NotImplementedError

    def count_tokens(self, text):
        return max(1, len(text or "") // 3)
