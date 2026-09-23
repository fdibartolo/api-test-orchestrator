# API Test Orchestrator

[![CI](https://github.com/fdibartolo/api-test-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/fdibartolo/api-test-orchestrator/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/fdibartolo/api-test-orchestrator/graph/badge.svg?token=MK8W5643TU)](https://codecov.io/github/fdibartolo/api-test-orchestrator)

__API Test Orchestrator__ is a small middleware for executing API test requests and validating their responses. It can:

- Execute one or more HTTP requests in sequence.
- Apply anonymous, bearer-token, or token-endpoint authentication.
- Substitute shared variables and dynamic values before a request is sent.
- Validate status codes and JSON response content with JSONPath expressions.
- Extract values from a response and make them available to later requests.

Requests are processed in order and execution stops at the first request whose validation fails.

## What is this?

The project exposes a FastAPI endpoint:

```text
POST /validate
```

The endpoint accepts an `ApiTestRequestVMList` payload and returns one result per executed request. A successful result has `isValidationSuccess: true`; failures include details in `failedValidations`.

## How do I install it?

Requirements:

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/) for environment and dependency management

From the repository root, install the project and its development dependencies:

```bash
uv sync --all-groups
```

To install only runtime dependencies, use:

```bash
uv sync
```

The application loads a `.env` file automatically. The built-in secret names used by the application are:

```dotenv
AZURE_AD_CLIENT_SECRET=your-client-secret
TEST_ID_PASSWORD=your-test-password
```

Do not commit real credentials or `.env` files to source control.

## How do I run it?

Start the development server from the repository root:

```bash
uv run fastapi [dev]
```

The API is then available at `http://127.0.0.1:8000`. FastAPI's interactive documentation is available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### Docker

Build and run the image locally:

```bash
docker build --tag apitest .
docker run --rm --publish 8000:8000 --env-file .env apitest
```

## How do I use it?

Send a `POST` request to `/validate` with JSON such as:

```json
{
	"authenticationParams": {
		"type": "Bearer",
		"tokenProvided": "your-access-token"
	},
	"apiTestRequests": [
		{
			"id": "get-user",
			"url": "https://api.example.test/users/42",
			"method": "GET",
			"headers": {
				"Accept": "application/json"
			},
			"expectedResponse": {
				"status": 200,
				"contentValidations": {
					"$.id": {
						"type": "equals",
						"value": 42
					},
					"$.roles": {
						"type": "contains",
						"value": "reader"
					}
				}
			},
			"variables": {
				"userName": "$.name"
			}
		}
	],
	"globalVariables": {}
}
```

For example, with `curl`:

```bash
curl --request POST \
	--url http://127.0.0.1:8000/validate \
	--header 'Content-Type: application/json' \
	--data @request.json
```

### Request fields

- `authenticationParams`: Optional shared authentication. Supported `type` values are `Anonymous`, `Bearer`, and `Basic`. A bearer token can be supplied with `tokenProvided`. Token endpoint authentication uses `credentials` with `grantType` set to `client_credentials` or `password`.
- `apiTestRequests`: Requests to execute, in order. Each request needs `id`, `url`, and `method`. It may also include `headers`, `cookies`, `queryParams`, `jsonBody`, `expectedResponse`, `variables`, and `waitForEventPropagation`.
- `globalVariables`: Required dictionary of values available to every request.
- `expectedResponse.status`: Expected HTTP status; defaults to `200`.
- `expectedResponse.contentValidations`: A map of JSONPath expressions to validation rules. Find below the available response validation types.
- `variables`: Maps a variable name to a JSONPath expression. Values extracted from a response are added to `globalVariables` for subsequent requests.
- `waitForEventPropagation`: Optional request-level value, in seconds, that introduces a quick halt after a successful request to give time between requests for event propagation or other asynchronous processing.

#### Available response validation types

The validator evaluates each JSONPath rule in `expectedResponse.contentValidations` against the response body. The supported validation types are:

- `fieldnotexists`: if the JSONPath resolves to a value, the validation fails immediately because the field should not exist.
- `equals`: compares the actual value to the expected value with case-insensitive string comparison when either side is a string.
- `notequals`: the inverse of `equals`.
- `contains`: for lists, returns true when any item matches the expected value; for strings, tests whether the expected text is contained within the actual string (case-insensitive).
- `notcontains`: for lists, returns true when no item matches the expected value; for non-list values, the implementation treats the result as effectively valid.
- `containsall`: for list-to-list validation, returns true only when every expected item appears somewhere in the actual list.
- `containspropertywithvalue`: for a list of objects, returns true when at least one item has a property matching the expected name/value pair. The expected payload must be a single-property object such as `{ "status": "active" }`.
- `length`: checks whether the actual value length equals the expected integer. This works for lists, dictionaries, and strings.
- `notnull`: succeeds when the value is not `None`.
- `null`: succeeds when the value is `None`.
- `notempty`: succeeds when the value is not `None` and its trimmed string representation is not empty.
- `empty`: succeeds when the value is `None` or its trimmed string representation is empty.

Finally, if a JSONPath is invalid or the expression does not resolve to a token, the validation result is recorded as a `SelectToken` failure rather than a value mismatch. That means malformed paths and missing fields are both surfaced clearly in `failedValidations`.


### Variable substitution

Use `#{variableName}#` in URLs, headers, cookies, query parameters, JSON bodies, and validation values. For example:

```json
{
	"url": "https://api.example.test/users/#{userId}#",
	"queryParams": {
		"environment": "#{environment}#"
	}
}
```

Variables can come from two places: the root-level `globalVariables` object, or a request-level `variables` object that extracts values from the response of that request.

#### Root-level variables

Define shared values in `globalVariables`. They are applied to every request in `apiTestRequests`, in execution order. Use the variable name without the `#{` and `}#` delimiters as the JSON property name:

```json
{
	"globalVariables": {
		"baseUrl": "https://api.example.test",
		"environment": "test",
		"tenantId": "tenant-42"
	},
	"apiTestRequests": [
		{
			"id": "get-settings",
			"url": "#{baseUrl}#/tenants/#{tenantId}#/settings",
			"method": "GET",
			"queryParams": {
				"environment": "#{environment}#"
			}
		}
	]
}
```

Substitution is supported in request URLs, headers, cookies, query parameters, JSON bodies, request-level variable definitions, and response-validation paths, values, and error messages. If a variable is not defined, its placeholder is left unchanged. Values are substituted as strings; for example, replacing `#{count}#` with `3` in a JSON body produces the string value `"3"`, not the number `3`.

#### Request-level variables

Define request-level variables as a map from the name you want to store to a JSONPath expression evaluated against that request's response. The first matching value is stored, then merged into `globalVariables` and made available to subsequent requests:

```json
{
	"globalVariables": {
		"baseUrl": "https://api.example.test"
	},
	"apiTestRequests": [
		{
			"id": "create-user",
			"url": "#{baseUrl}#/users",
			"method": "POST",
			"jsonBody": {
				"name": "Ada"
			},
			"variables": {
				"userId": "$.id",
				"userName": "$.name"
			}
		},
		{
			"id": "get-created-user",
			"url": "#{baseUrl}#/users/#{userId}#",
			"method": "GET",
			"expectedResponse": {
				"contentValidations": {
					"$.name": {
						"type": "equals",
						"value": "#{userName}#"
					}
				}
			}
		}
	]
}
```

In this example, the first response's `id` and `name` become `userId` and `userName`. The second request can use both values through the same `#{variableName}#` syntax. If a JSONPath does not find a value, the variable is not stored and the request result includes a `SelectToken` validation failure. Since execution stops after the first failed validation, later requests are not sent.

Dynamic placeholders are resolved in `jsonBody` and `queryParams` before each request is sent. Values are evaluated in UTC. Placeholders can appear anywhere in a string, including between a prefix and suffix, and placeholders inside nested objects and arrays are supported. Other scalar values are left unchanged.

#### Available dynamic placeholders

| Placeholder | Syntax | Default output | Description |
| --- | --- | --- | --- |
| Today | `{{DynamicToday}}` | `yyyy-MM-dd` | The current UTC date. |
| Current time | `{{DynamicNow}}` | `yyyy-MM-dd HH:mm:ssZ` | The current UTC date and time. The trailing `Z` indicates UTC. |
| Future time | `{{DynamicFuture}}:<amount><unit>` | `yyyy-MM-dd HH:mm:ssZ` | The current UTC date and time plus an offset. |
| Past time | `{{DynamicPast}}:<amount><unit>` | `yyyy-MM-dd HH:mm:ssZ` | The current UTC date and time minus an offset. |
| Random number | `{{DynamicRandomNumber}}:<digits>` | None | A random number with exactly the requested number of digits. |
| Random GUID | `{{DynamicRandomGuid}}` | UUID format | A randomly generated UUID v4. |

For `DynamicFuture` and `DynamicPast`, the supported units are:

- `d`: days
- `h`: hours
- `m`: minutes

Examples:

```json
{
	"today": "{{DynamicToday}}",
	"timestamp": "{{DynamicNow}}",
	"tomorrow": "{{DynamicFuture}}:1d",
	"one_hour_ago": "{{DynamicPast}}:1h",
	"random_id": "{{DynamicRandomNumber}}:8",
	"correlation_id": "{{DynamicRandomGuid}}"
}
```

#### Custom date and time formats

`DynamicToday`, `DynamicNow`, `DynamicFuture`, and `DynamicPast` accept an optional format after a second colon:

```text
{{DynamicToday}}:yyyy/MM/dd
{{DynamicNow}}:yyyy-MM-dd'T'HH:mm:ss
{{DynamicFuture}}:2h:yyyy-MM-dd HH:mm
{{DynamicPast}}:7d:yyMMdd
```

The supported format tokens are:

| Token | Meaning |
| --- | --- |
| `yyyy` | Four-digit year |
| `yy` | Two-digit year |
| `MM` | Two-digit month |
| `dd` | Two-digit day of month |
| `HH` | Two-digit hour, 00-23 |
| `mm` | Two-digit minute |
| `ss` | Two-digit second |

Separators and other literal characters are passed through to the resulting format. If no custom format is provided, `DynamicToday` returns `yyyy-MM-dd`, and the other date/time placeholders return `yyyy-MM-dd HH:mm:ssZ`.

`DynamicRandomNumber` requires a positive digit count, for example `{{DynamicRandomNumber}}:6`. `DynamicRandomGuid` returns a lowercase UUID v4 such as `550e8400-e29b-41d4-a716-446655440000`.

## How do I generate API test samples with AI?

The repository ships an `api-learner` agent definition in `.github/agents/api-learner.agent.md`. In an AI-enabled editor that supports repository agents, invoke `api-learner` and provide an API endpoint URL or an OpenAPI document path. The agent reads the API contract and generates representative `/validate` request samples under `samples/` folder.

The agent instructions are included in this repository for you to use with your own AI subscription. The repository does not provide an AI service, subscription, credentials, or access to the target API. The agent only inspects the OpenAPI document. Review generated samples and replace placeholder values if needed, before running them.

## How do I run tests?

Run the complete test suite with:

```bash
uv run pytest
```

Run the test suite with coverage-style output for a specific area, for example:

```bash
uv run pytest tests/services/test_orchestrator_service.py -q
```

Run the project's linter with:

```bash
uv run ruff check .
uv run ruff format --check .
```
