# Bruno API Requests

Set Bruno's `baseUrl` environment variable to `http://127.0.0.1:8000`.

## Get Students

**GET** `{{baseUrl}}/students`

Expected: `200 OK`, with a JSON array of students:

```json
[
  {
    "id": 1,
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.edu"
  }
]
```

## Get One Student

**GET** `{{baseUrl}}/students/1`

Expected: `200 OK` with Ada's student object. A missing ID returns `404`:

```json
{"detail":"Student not found"}
```

## Get a Student's Classes

**GET** `{{baseUrl}}/students/1/classes`

Expected: `200 OK`, with Ada's classes. Each object has `id`, `name`, `subject`, and `student_id`.

## Get All Classes

**GET** `{{baseUrl}}/classes`

Expected: `200 OK`, with a JSON array of class objects.

## Create a Student

**POST** `{{baseUrl}}/students`

Set the request body type to JSON and paste:

```json
{
  "first_name": "Grace",
  "last_name": "Hopper",
  "email": "grace.hopper+bruno@example.edu"
}
```

Expected: `201 Created`, with the saved student object. Its `id` is assigned by PostgreSQL.

## Validate Email

**POST** `{{baseUrl}}/students`

```json
{
  "first_name": "Grace",
  "last_name": "Hopper",
  "email": "not-an-email"
}
```

Expected: `422 Unprocessable Entity`, with a `detail` array describing the invalid email.

## Validate Required Names

**POST** `{{baseUrl}}/students`

```json
{
  "first_name": "  ",
  "last_name": "Hopper",
  "email": "grace.hopper@example.edu"
}
```

Expected: `422 Unprocessable Entity`, because `first_name` is blank after trimming.

## Duplicate Email

Send the successful create request again with the same email.

Expected: `409 Conflict`:

```json
{"detail":"A student with this email already exists"}
```