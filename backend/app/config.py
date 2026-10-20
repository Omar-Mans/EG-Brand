import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

AI_KEY_VARS = ("GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "TOGETHERAI_API_KEY")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "sqlite:///./egbrand.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    token_encryption_key: str = ""  # Fernet key for social tokens; derived from jwt_secret when empty (dev only)
    cors_origins: str = "http://localhost:3000"
    public_base_url: str = "http://localhost:8000"  # where uploaded images are served from
    frontend_url: str = "http://localhost:3000"
    admin_emails: str = ""  # comma-separated; these users see cost across all companies

    # Background work: run the worker loop inside the API process (dev) or as its own process (prod)
    embedded_worker: bool = True
    worker_poll_seconds: int = 10

    # AI
    ai_mode: str = "auto"  # auto | mock | live
    llm_fast_models: str = "groq/openai/gpt-oss-20b"
    llm_quality_models: str = "groq/openai/gpt-oss-120b,groq/qwen/qwen3.8-27b"
    llm_timeout_seconds: int = 120
    # Fallback prices when the gateway has no price for a model: "model=in_per_million:out_per_million;..."
    llm_price_overrides: str = ""
    default_monthly_ai_budget_usd: float = 5.0

    # AI background photos. auto: fal (paid) > Cloudflare Workers AI (free tier) > pollinations (free, no key) > mock
    image_provider: str = "auto"  # auto | fal | cloudflare | pollinations | mock
    fal_key: str = ""
    fal_model: str = "fal-ai/flux/schnell"
    image_cost_usd: float = 0.003  # per fal image, for the cost page
    cf_account_id: str = ""
    cf_api_token: str = ""
    cf_image_model: str = "@cf/black-forest-labs/flux-1-schnell"
    # Real stock photos (free for commercial use, no attribution required)
    pexels_api_key: str = ""
    pixabay_api_key: str = ""

    # External scheduler (e.g. cron-job.org) can call /api/cron/tick when free hosting sleeps
    cron_secret: str = ""

    # Arabic voice-over for reels. auto = azure (official free tier) if a key is set, else edge (free, no key), else mock
    tts_provider: str = "auto"  # auto | azure | edge | mock
    azure_speech_key: str = ""
    azure_speech_region: str = "uaenorth"
    ffmpeg_bin: str = "ffmpeg"

    # Storage for rendered images (must be publicly reachable for Instagram publishing)
    storage_backend: str = "local"  # local | s3
    upload_dir: str = "./uploads"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""  # e.g. Cloudflare R2 endpoint
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_public_base_url: str = ""

    # Social publishing
    social_mode: str = "auto"  # auto | mock | live
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_version: str = "v23.0"
    meta_redirect_path: str = "/api/social/meta/callback"

    @property
    def ai_live(self) -> bool:
        if self.ai_mode == "mock":
            return False
        if self.ai_mode == "live":
            return True
        return any(os.environ.get(k) for k in AI_KEY_VARS)

    @property
    def image_backend(self) -> str:
        if self.image_provider != "auto":
            return self.image_provider
        if self.fal_key:
            return "fal"
        if self.cf_account_id and self.cf_api_token:
            return "cloudflare"
        return "pollinations" if self.ai_live else "mock"

    @property
    def stock_backend(self) -> str:
        if self.pexels_api_key:
            return "pexels"
        if self.pixabay_api_key:
            return "pixabay"
        return "mock" if not self.ai_live else ""

    @property
    def voice_backend(self) -> str:
        if self.tts_provider != "auto":
            return self.tts_provider
        if self.azure_speech_key:
            return "azure"
        return "edge" if self.ai_live else "mock"

    @property
    def social_live(self) -> bool:
        if self.social_mode == "mock":
            return False
        if self.social_mode == "live":
            return True
        return bool(self.meta_app_id and self.meta_app_secret)

    def model_list(self, tier: str) -> list[str]:
        raw = self.llm_quality_models if tier == "quality" else self.llm_fast_models
        return [m.strip() for m in raw.split(",") if m.strip()]

    def price_overrides(self) -> dict[str, tuple[float, float]]:
        out: dict[str, tuple[float, float]] = {}
        for part in self.llm_price_overrides.split(";"):
            if "=" not in part:
                continue
            name, prices = part.split("=", 1)
            try:
                i, o = prices.split(":")
                out[name.strip()] = (float(i), float(o))
            except ValueError:
                continue
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
