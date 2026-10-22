import hashlib
import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .models import SchoolClass, Student

DatabaseSession = Annotated[Session, Depends(get_session)]
IfNoneMatchHeader = Annotated[str | None, Header()]

class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    version: int


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    student_id: int


def _matches_if_none_match(if_none_match: str | None, etag: str) -> bool:
    if if_none_match is None:
        return False
    return any(
        tag.strip() in {"*", etag, f"W/{etag}"}
        for tag in if_none_match.split(",")
    )


def _etag_for(content: object) -> str:
    body = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f'"{hashlib.sha256(body.encode("utf-8")).hexdigest()}"'


def _conditional_response(
    etag: str,
    if_none_match: str | None,
    response: Response,
) -> Response | None:
    response.headers["ETag"] = etag
    if _matches_if_none_match(if_none_match, etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    return None


app = FastAPI()


@app.get("/", response_model=None)
def read_root(
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> dict[str, str] | Response:
    payload = {"message": "Hello from kigs!"}
    not_modified = _conditional_response(
        _etag_for(payload),
        if_none_match,
        response,
    )
    return not_modified if not_modified is not None else payload


@app.get("/students", response_model=list[StudentResponse])
def read_students(
    database_session: DatabaseSession,
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> list[Student] | Response:
    statement = select(Student).order_by(Student.id)
    students = list(database_session.scalars(statement).all())
    content = [
        StudentResponse.model_validate(student).model_dump(mode="json")
        for student in students
    ]
    not_modified = _conditional_response(
        _etag_for(content),
        if_none_match,
        response,
    )
    return not_modified if not_modified is not None else students


@app.get("/students/{student_id}", response_model=StudentResponse)
def read_student(
    student_id: int,
    database_session: DatabaseSession,
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> Student | Response:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    etag = f'"{student.version}"'
    not_modified = _conditional_response(etag, if_none_match, response)
    return not_modified if not_modified is not None else student


@app.get("/student", response_model=StudentResponse)
def read_student_by_query(
    student_id: Annotated[int, Query(gt=0)],
    database_session: DatabaseSession,
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> Student | Response:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    etag = f'"{student.version}"'
    not_modified = _conditional_response(etag, if_none_match, response)
    return not_modified if not_modified is not None else student


@app.get("/students/{student_id}/classes", response_model=list[ClassResponse])
def read_student_classes(
    student_id: int,
    database_session: DatabaseSession,
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> list[SchoolClass] | Response:
    if database_session.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    statement = (
        select(SchoolClass)
        .where(SchoolClass.student_id == student_id)
        .order_by(SchoolClass.id)
    )
    classes = list(database_session.scalars(statement).all())
    content = [
        ClassResponse.model_validate(school_class).model_dump(mode="json")
        for school_class in classes
    ]
    not_modified = _conditional_response(
        _etag_for(content),
        if_none_match,
        response,
    )
    return not_modified if not_modified is not None else classes


@app.get("/classes", response_model=list[ClassResponse])
def read_classes(
    database_session: DatabaseSession,
    response: Response,
    if_none_match: IfNoneMatchHeader = None,
) -> list[SchoolClass] | Response:
    statement = select(SchoolClass).order_by(SchoolClass.id)
    classes = list(database_session.scalars(statement).all())
    content = [
        ClassResponse.model_validate(school_class).model_dump(mode="json")
        for school_class in classes
    ]
    not_modified = _conditional_response(
        _etag_for(content),
        if_none_match,
        response,
    )
    return not_modified if not_modified is not None else classes