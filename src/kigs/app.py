import hashlib
import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from .database import get_session
from .models import SchoolClass, Student

DatabaseSession = Annotated[Session, Depends(get_session)]
IfMatchHeader = Annotated[str | None, Header()]
IfNoneMatchHeader = Annotated[str | None, Header()]


NonBlankName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class StudentCreate(BaseModel):
    first_name: NonBlankName
    last_name: NonBlankName
    email: EmailStr


class StudentUpdate(StudentCreate):
    version: int = Field(ge=1)


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


def _matches_if_match(if_match: str, version: int) -> bool:
    current_etag = f'"{version}"'
    return any(
        tag.strip() in {"*", current_etag}
        for tag in if_match.split(",")
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


@app.post(
    "/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student(
    student_data: StudentCreate,
    database_session: DatabaseSession,
) -> Student:
    student = Student(
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        email=str(student_data.email),
    )
    database_session.add(student)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "students_email_key":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A student with this email already exists",
            ) from error
        raise
    database_session.refresh(student)
    return student


@app.put("/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    database_session: DatabaseSession,
    response: Response,
    if_match: IfMatchHeader = None,
) -> Student:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if if_match is not None and not _matches_if_match(if_match, student.version):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="If-Match does not match the current student version",
        )
    if student.version != student_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student has changed; fetch the latest version and retry",
        )

    student.first_name = student_data.first_name
    student.last_name = student_data.last_name
    student.email = str(student_data.email)
    try:
        database_session.commit()
    except StaleDataError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_412_PRECONDITION_FAILED
                if if_match is not None
                else status.HTTP_409_CONFLICT
            ),
            detail="Student was updated concurrently; fetch the latest version and retry",
        ) from error
    except IntegrityError as error:
        database_session.rollback()
        if getattr(getattr(error.orig, "diag", None), "constraint_name", None) == "students_email_key":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A student with this email already exists",
            ) from error
        raise
    database_session.refresh(student)
    response.headers["ETag"] = f'"{student.version}"'
    return student


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    database_session: DatabaseSession,
    if_match: IfMatchHeader = None,
) -> Response:
    student = database_session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if if_match is not None and not _matches_if_match(if_match, student.version):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="If-Match does not match the current student version",
        )

    try:
        database_session.delete(student)
        database_session.commit()
    except StaleDataError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_412_PRECONDITION_FAILED
                if if_match is not None
                else status.HTTP_409_CONFLICT
            ),
            detail="Student was updated concurrently; fetch the latest version and retry",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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