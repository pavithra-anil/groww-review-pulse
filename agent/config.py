from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
import os


class Product(BaseModel):
    name: str
    display_name: str
    play_store_id: str
    app_store_id: str
    app_store_country: str = "in"
    weeks: int = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    groq_api_key: str
    mcp_server_url: str = ""
    confirm_send: bool = False

    products: list[Product] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_products()

    def _load_products(self):
        products_file = "products.yaml"
        if not os.path.exists(products_file):
            raise FileNotFoundError(
                f"products.yaml not found. Please create it in the project root.\n"
                f"See products.yaml in the repo for an example."
            )
        with open(products_file, "r") as f:
            data = yaml.safe_load(f)
        self.products = [Product(**p) for p in data.get("products", [])]

    def get_product(self, name: str) -> Product:
        for p in self.products:
            if p.name == name:
                return p
        raise ValueError(
            f"Product '{name}' not found in products.yaml. "
            f"Available: {[p.name for p in self.products]}"
        )


settings = Settings()