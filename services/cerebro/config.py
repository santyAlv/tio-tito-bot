from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # sqlite:///data/tiotito.db  (gratis, liviano)
    # postgresql://...           (si ya tenés Postgres)
    database_url: str = "sqlite:///data/tiotito.db"

    # groq = gratis, sin RAM local (recomendado)
    # ollama = 100% local/gratis
    # openai = de pago
    llm_provider: str = "groq"

    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.6-27b"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:0.5b"
    ollama_timeout: int = 300
    ollama_contexto_mensajes: int = 15

    grupo_jid: str = ""
    responder_privado: bool = True
    trigger_words: str = "tio tito,tío tito,tito"
    contexto_mensajes: int = 40
    mensajes_auto_probabilidad: float = 0.6
    max_respuestas_dia: int = 25

    prompts_dir: str = "prompts"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def uses_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
