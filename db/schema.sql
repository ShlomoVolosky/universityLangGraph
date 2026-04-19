CREATE TABLE teachers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    department TEXT
);

CREATE TABLE students (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    enrollment_year INTEGER
);

CREATE TABLE courses (
    id      INTEGER PRIMARY KEY,
    title   TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE course_offerings (
    id         INTEGER PRIMARY KEY,
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    semester   TEXT    NOT NULL,
    UNIQUE (course_id, teacher_id, semester)
);

CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    offering_id INTEGER NOT NULL REFERENCES course_offerings(id),
    grade       REAL,
    UNIQUE (student_id, offering_id)
);

CREATE INDEX idx_enrollments_offering ON enrollments(offering_id);
CREATE INDEX idx_enrollments_student  ON enrollments(student_id);
CREATE INDEX idx_offerings_semester   ON course_offerings(semester);
