import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    webhook_url: str = os.getenv("WEBHOOK_URL", "").rstrip("/")
    webhook_path: str = os.getenv("WEBHOOK_PATH", "/webhook")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    port: int = int(os.getenv("PORT", "10000"))
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "1400"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    delete_webhook_on_shutdown: bool = (
        os.getenv("DELETE_WEBHOOK_ON_SHUTDOWN", "false").lower() == "true"
    )
    system_prompt: str = os.getenv(
        "SYSTEM_PROMPT",
        (
            "You are Gemini inside a premium Telegram bot. Give clear, useful answers. "
            "Use concise structure when helpful, but do not overuse markdown."
        ),
    )

    def normalized_webhook_path(self) -> str:
        if self.webhook_path.startswith("/"):
            return self.webhook_path
        return f"/{self.webhook_path}"

    def webhook_endpoint(self) -> str:
        return f"{self.webhook_url}{self.normalized_webhook_path()}"

    def validate(self) -> None:
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
