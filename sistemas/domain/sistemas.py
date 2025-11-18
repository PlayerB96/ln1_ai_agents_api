import re
from typing import Dict
from unicodedata import name

from sistemas.domain.dataModel.model import JiraRequest
from fastapi import APIRouter
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from sistemas.infrastructure.controller import SistemasController


sistemas = APIRouter()

@sistemas.post("/agent/jira", tags=["Jira Agent Sistemas"])
def process_jira_request(data: JiraRequest):
    controller = SistemasController(data)
    return controller.process_request()
