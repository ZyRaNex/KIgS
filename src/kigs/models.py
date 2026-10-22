from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    __table_args__ = {"schema": "school"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="student")


class SchoolClass(Base):
    __tablename__ = "classes"
    __table_args__ = {"schema": "school"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("school.students.id", ondelete="CASCADE"),
        nullable=False,
    )
    student: Mapped[Student] = relationship(back_populates="classes")