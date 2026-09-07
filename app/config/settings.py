from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    apify_api_token: str = ""
    apify_instagram_profile_actor: str = "parseforge/instagram-posts-scraper"
    apify_instagram_post_actor: str = "parseforge/instagram-posts-scraper"
    apify_linkedin_profile_actor: str = "data-slayer/linkedin-profile-posts-scraper"
    apify_linkedin_post_actor: str = "fetch_cat/linkedin-posts-scraper"
    apify_facebook_profile_actor: str = "spbotdel/facebook-profile-posts-all-photos-scraper"
    apify_facebook_post_actor: str = "scrapyspider/facebook-post-scraper"
    apify_reddit_profile_actor: str = "scrapers_lat/reddit-scraper"
    apify_reddit_post_actor: str = "scrapers_lat/reddit-scraper"
    max_posts_per_profile: int = 30
    max_candidates: int = 50
    face_match_threshold: float = 0.45
    base_sepolia_rpc_url: str = ""
    blockchain_private_key: str = ""
    evidence_registry_address: str = ""
    data_dir: str = "./var"

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), env_prefix="", case_sensitive=False)


settings = Settings()
