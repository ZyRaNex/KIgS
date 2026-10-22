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
    "email": "ada@example.edu",
    "version": 1
  }
]
```

## Get One Student

**GET** `{{baseUrl}}/students/1`

Expected: `200 OK` with Ada's student object. A missing ID returns `404`:

```json
{"detail":"Student not found"}
```

## Get One Student by Query

**GET** `{{baseUrl}}/student?student_id=1`

Expected: the same student response and version-based `ETag` as `GET /students/1`. A missing student returns `404`; a missing, non-integer, or non-positive `student_id` returns `422`.

Every GET response includes an `ETag`. For this endpoint, the ETag is the student's `version`, for example `"1"`. The other GET endpoints use an ETag derived from their response data. To make a conditional request, repeat the same GET and copy its ETag into this Bruno header:

| Name | Value |
| --- | --- |
| `If-None-Match` | `"1"` |

Expected: `304 Not Modified` with an empty body when the response is unchanged. If its ETag has changed, the response is `200 OK` with the current representation and ETag.

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

Expected: `201 Created`, with the saved student object. PostgreSQL assigns its `id`; its initial `version` is `1`.

## Create a Class

**POST** `{{baseUrl}}/classes`

Set the request body type to JSON and paste:

```json
{
  "name": "Geometry",
  "subject": "Mathematics",
  "student_id": 1
}
```

Expected: `201 Created`, with the saved class object including its assigned `id`. A missing student returns `404`; blank `name`/`subject` or a non-positive `student_id` returns `422`.

## Update a Student

First run `GET {{baseUrl}}/students/1` and use the returned `version` value.

**PUT** `{{baseUrl}}/students/1`

Add this Bruno request header using the ETag returned by GET:

| Name | Value |
| --- | --- |
| `If-Match` | `"1"` |

```json
{
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@example.edu",
  "version": 1
}
```

Expected: `200 OK`, with the updated student and an incremented `version` (`2` in this example). The response ETag is updated to `"2"`.

To verify lost-update protection, send the same PUT again with the old `If-Match` value (`"1"`). It returns `412 Precondition Failed`. GET the student again and retry using its current ETag and body version. The body `version` is also checked; without an `If-Match` header, a stale body version returns `409 Conflict`.

An invalid email, blank name, or missing/less-than-one version returns `422 Unprocessable Entity`.

## Delete a Student

First run `GET {{baseUrl}}/students/{id}` and use its current `ETag`.

**DELETE** `{{baseUrl}}/students/{id}`

Add this header with the quoted version from the GET response:

| Name | Value |
| --- | --- |
| `If-Match` | `"1"` |

Expected: `204 No Content`. The student's classes are deleted through the foreign-key cascade. A stale ETag returns `412`; deleting a missing student returns `404`.

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