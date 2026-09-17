# API Test Orchestrator

[![CI](https://github.com/fdibartolo/api-test-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/fdibartolo/api-test-orchestrator/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/fdibartolo/api-test-orchestrator/graph/badge.svg?token=MK8W5643TU)](https://codecov.io/github/fdibartolo/api-test-orchestrator)

__API Test Orchestrator__ is a small Python/FastAPI middleware for executing API test requests and validating their responses. It can:

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

The package also defines an `apitest` console command. At present, that command is a basic entry-point smoke check; use Uvicorn to run the HTTP API.

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
- `apiTestRequests`: Requests to execute, in order. Each request needs `id`, `url`, and `method`. It may also include `headers`, `cookies`, `queryParams`, `jsonBody`, `expectedResponse`, and `variables`.
- `globalVariables`: Required dictionary of values available to every request.
- `expectedResponse.status`: Expected HTTP status; defaults to `200`.
- `expectedResponse.contentValidations`: A map of JSONPath expressions to validation rules. Supported types include `equals`, `notequals`, `contains`, `notcontains`, `containsall`, `containspropertywithvalue`, `length`, `notnull`, `null`, `notempty`, `empty`, and `fieldnotexists`.
- `variables`: Maps a variable name to a JSONPath expression. Values extracted from a response are added to `globalVariables` for subsequent requests.

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
