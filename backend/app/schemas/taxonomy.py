from pydantic import BaseModel, ConfigDict, Field


class NamedEntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class NamedEntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

