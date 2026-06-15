from collections import defaultdict, deque
from dataclasses import dataclass, field

from .config import settings


@dataclass
class UserSettings:
    temperature: float = 0.7
    temperature_label: str = "Balanced"
    concise_mode: bool = False
    rich_ui: bool = True
    total_tokens: int = 0
    prompt_tokens: int = 0
    response_tokens: int = 0
    history: deque = field(
        default_factory=lambda: deque(maxlen=settings.max_history_messages)
    )


class InMemoryDatabase:
    def __init__(self) -> None:
        self.users: defaultdict[int, UserSettings] = defaultdict(UserSettings)

    def get_user(self, chat_id: int) -> UserSettings:
        return self.users[chat_id]

    def clear_history(self, chat_id: int) -> None:
        self.users[chat_id].history.clear()

    def add_exchange(self, chat_id: int, user_text: str, assistant_text: str) -> None:
        user = self.get_user(chat_id)
        user.history.append({"role": "user", "text": user_text})
        user.history.append({"role": "assistant", "text": assistant_text})

    def add_token_usage(
        self,
        chat_id: int,
        prompt_tokens: int = 0,
        response_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        user = self.get_user(chat_id)
        user.prompt_tokens += prompt_tokens
        user.response_tokens += response_tokens
        user.total_tokens += total_tokens or prompt_tokens + response_tokens


db = InMemoryDatabase()
