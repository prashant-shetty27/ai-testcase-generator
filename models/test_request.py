from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# =====================================
# PLATFORM
# =====================================

class PlatformEnum(str, Enum):
    web = "web"
    touch = "touch"
    api = "api"
    android_app = "android_app"
    ios_app = "ios_app"
    hybrid_app = "hybrid_app"
    backend = "backend"
    internal = "internal"


# =====================================
# PRODUCT
# =====================================

class ProductEnum(str, Enum):
    b2c = "b2c"
    b2b = "b2b"
    leads = "leads"
    vertical = "vertical"   # ✔ kept as requested
    ubl = "ubl"
    internal = "internal"


# =====================================
# MODULE
# =====================================

class ModuleEnum(str, Enum):
    login = "login"
    dashboard = "dashboard"
    reports = "reports"
    search = "search"
    home = "home"
    profile = "profile"
    settings = "settings"
    result = "result"
    details = "details"
    prp = "prp"
    pdp = "pdp"
    catalogue = "catalogue"
    verticals = "verticals"
    payment_gateway = "payment_gateway"
    autosuggest = "autosuggest"
    chatbot = "chatbot"
    voice_assistant = "voice_assistant"
    ui = "ui"
    data = "data"
    leads = "leads"
    analytics = "analytics"
    sales = "sales"
    finance = "finance"
    cs = "cs"
    dc = "dc"
    kyc = "kyc"
    movies = "movies"
    restaurants = "restaurants"
    real_estate = "real_estate"
    healthcare = "healthcare"
    home_services = "home_services"
    beauty = "beauty"
    education = "education"
    hotels = "hotels"
    jobs = "jobs"
    legal = "legal"
    matrimony = "matrimony"
    pets = "pets"
    events = "events"
    notifications = "notifications"
    sync = "sync"
    integrations = "integrations"
    others = "others"


# =====================================
# PAGE
# =====================================

class PageEnum(str, Enum):
    login_page = "login_page"
    home_page = "home_page"
    result_page = "result_page"
    details_page = "details_page"
    prp_page = "prp_page"
    pdp_page = "pdp_page"
    catalogue_page = "catalogue_page"

    leads_dashboard = "leads_dashboard"
    analytics_dashboard = "analytics_dashboard"
    leads_page = "leads_page"

    edit_listings_page = "edit_listings_page"
    free_listings_page = "free_listings_page"

    payment_gateway_page = "payment_gateway_page"
    user_profile_page = "user_profile_page"
    settings_page = "settings_page"
    reports_page = "reports_page"
    search_page = "search_page"
    notification = "notification"
    reviews_ratings = "reviews_ratings"

    ubl_android_app = "ubl_android_app"
    ubl_ios_app = "ubl_ios_app"

    vn_an_dvn_calls = "vn_an_dvn_calls"
    leads_dashboard_page = "leads_dashboard_page"
    analytics_dashboard_page = "analytics_dashboard_page"

    web_b2b_rfq_page = "web_b2b_rfq_page"
    web_b2b_home_page = "web_b2b_home_page"
    web_b2b_prp_page = "web_b2b_prp_page"
    web_b2b_pdp_page = "web_b2b_pdp_page"
    web_b2b_catalogue_page = "web_b2b_catalogue_page"

    touch_b2b_rfq_page = "touch_b2b_rfq_page"
    touch_b2b_home_page = "touch_b2b_home_page"
    touch_b2b_prp_page = "touch_b2b_prp_page"
    touch_b2b_pdp_page = "touch_b2b_pdp_page"
    touch_b2b_catalogue_page = "touch_b2b_catalogue_page"

    android_b2b_rfq_page = "android_b2b_rfq_page"
    android_b2b_home_page = "android_b2b_home_page"
    android_b2b_prp_page = "android_b2b_prp_page"
    android_b2b_pdp_page = "android_b2b_pdp_page"
    android_b2b_catalogue_page = "android_b2b_catalogue_page"

    ios_b2b_rfq_page = "ios_b2b_rfq_page"
    ios_b2b_home_page = "ios_b2b_home_page"
    ios_b2b_prp_page = "ios_b2b_prp_page"
    ios_b2b_pdp_page = "ios_b2b_pdp_page"
    ios_b2b_catalogue_page = "ios_b2b_catalogue_page"

    autosuggest = "autosuggest"
    chatbot = "chatbot"
    voice_assistant = "voice_assistant"

    api_authentication = "api_authentication"

    genio = "genio"
    cs = "cs"
    dc = "dc"
    kyc = "kyc"
    de_cs = "de_cs"
    sales = "sales"
    finance = "finance"

    data = "data"
    performance = "performance"
    security = "security"
    others = "others"

# =====================================
# TEST TYPE
# =====================================

class TestTypeEnum(str, Enum):
    unit = "unit"
    uat = "uat"
    sanity = "sanity"
    regression = "regression"
    ui = "ui"
    functional = "functional"
    data = "data"
    e2e = "e2e"


# =====================================
# REQUEST MODEL
# =====================================

class TestGenerationRequest(BaseModel):

    model_config = ConfigDict(use_enum_values=True)

    requirement: str = Field(
        ...,
        example="User should login with username, password and captcha"
    )

    template: str = Field(default="manual")

    platforms: List[PlatformEnum] = Field(default_factory=list)
    product: Optional[ProductEnum] = None
    modules: List[ModuleEnum] = Field(default_factory=list)
    pages: List[PageEnum] = Field(default_factory=list)
    test_types: List[TestTypeEnum] = Field(default_factory=list)

    include_platform_tests: bool = False
    include_boundary_tests: bool = False
    include_parameter_tests: bool = False
    include_e2e_tests: bool = False

    existing_filename: Optional[str] = None
    update_comment: Optional[str] = None
    output_filename: Optional[str] = None

    enable_self_learning: bool = False
    learn_from_third_party: bool = False