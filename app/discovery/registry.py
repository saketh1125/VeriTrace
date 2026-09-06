from .apify_provider import FacebookApifyProvider, InstagramApifyProvider, LinkedInApifyProvider, RedditApifyProvider
from .models import Platform
from ..config.settings import Settings


def build_registry(settings: Settings):
    return {
        Platform.INSTAGRAM: InstagramApifyProvider(
            settings.apify_api_token,
            settings.apify_instagram_profile_actor,
            settings.apify_instagram_post_actor,
        ),
        Platform.LINKEDIN: LinkedInApifyProvider(
            settings.apify_api_token,
            settings.apify_linkedin_profile_actor,
            settings.apify_linkedin_post_actor,
        ),
        Platform.FACEBOOK: FacebookApifyProvider(
            settings.apify_api_token,
            settings.apify_facebook_profile_actor,
            settings.apify_facebook_post_actor,
        ),
        Platform.REDDIT: RedditApifyProvider(
            settings.apify_api_token,
            settings.apify_reddit_profile_actor,
            settings.apify_reddit_post_actor,
        ),
    }
