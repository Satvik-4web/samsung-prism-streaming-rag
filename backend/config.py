import os
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ControllerWeights(BaseModel):
    stability: float = 0.5
    completeness: float = 0.3
    info_gain: float = 0.2

class ControllerThresholds(BaseModel):
    retrieve: float = 0.75
    min_info_gain: float = 1.0
    debounce_ms: int = 200
    end_silence_ms: int = 1000

class ControllerSettings(BaseModel):
    weights: ControllerWeights = Field(default_factory=ControllerWeights)
    thresholds: ControllerThresholds = Field(default_factory=ControllerThresholds)

class Settings(BaseSettings):
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    controller: ControllerSettings = Field(default_factory=ControllerSettings)

    @classmethod
    def load(cls) -> "Settings":
        config_path = os.getenv("CONFIG_PATH", "configs/app.yaml")
        yaml_data: dict[str, Any] = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
                
        controller_path = os.getenv("CONTROLLER_CONFIG_PATH", "configs/controller.yaml")
        if os.path.exists(controller_path):
            with open(controller_path, "r", encoding="utf-8") as f:
                c_data = yaml.safe_load(f) or {}
                yaml_data["controller"] = c_data
        
        if "ENVIRONMENT" in os.environ:
            yaml_data["environment"] = os.environ["ENVIRONMENT"]
        
        return cls(**yaml_data)

settings = Settings.load()
