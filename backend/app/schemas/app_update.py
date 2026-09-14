from datetime import datetime

from pydantic import BaseModel, Field


class AppUpdateOut(BaseModel):
    version_code: int
    version_name: str
    download_url: str
    message: str = ""
    updated_at: datetime | None = None
    available: bool = Field(
        description="是否已配置有效更新（version_code>0 且 download_url 非空）",
    )
