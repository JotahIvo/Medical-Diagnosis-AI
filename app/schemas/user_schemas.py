import re

from pydantic import BaseModel, field_validator


class User(BaseModel):
    username: str
    password: str

    @field_validator('username')
    def validate_username(cls, value):
        if not re.match(r'^([a-z]|[0-9]|@)+$', 'value'):
            raise ValueError('Username format invalid')
        return value
