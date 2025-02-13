class Event:
    def __init__(self, event_type: str, payload: dict = None):
        self.event_type = event_type
        self.payload = payload or {}

class EventManager:
    def __init__(self):
        self.listeners = {}

    def add_listener(self, event_type: str, listener):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def remove_listener(self, event_type: str, listener):
        if event_type in self.listeners:
            self.listeners[event_type].remove(listener)

    def emit(self, event: Event):
        for listener in self.listeners.get(event.event_type, []):
            listener(event)

# Global event manager instance we can reuse throughout the system.
event_manager = EventManager()