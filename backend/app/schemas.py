from pydantic import BaseModel, Field


class IndexFolderRequest(BaseModel):
    path: str
    recursive: bool = True


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
