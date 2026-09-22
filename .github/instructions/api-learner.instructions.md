---
name: API Learner Request Format
description: "Use when generating JSON samples for the API Test Orchestrator /validate endpoint. Defines ApiTestRequestVMList, authentication, variables, requests, expected responses, and validations."
applyTo: "samples/**/*.json"
---

# Building an `ApiTestRequestVMList`

Generate each sample as one JSON object accepted by `POST /validate`. Build it from the root inward and use camelCase field names exactly as shown.

## Root: `ApiTestRequestVMList`

```json
{
	"authenticationParams": {
		"type": "Bearer",
		"tokenProvided": "<replace-with-access-token>"
	},
	"globalVariables": {
		"baseUrl": "https://api.example.com"
	},
	"apiTestRequests": []
}
```

- `authenticationParams` is optional shared authentication. Omit it for an unauthenticated API.
- `globalVariables` is required and must be an object of string keys and string values. Use `{}` when no variables are needed.
- `apiTestRequests` is required and is an ordered array of `ApiTestRequestVM` objects.
- Requests run sequentially and processing stops after the first failed status, content validation, or variable extraction.

## Authentication: `AuthInfoVM`

`authenticationParams` may appear at the root or on an individual request. Request-level authentication overrides root authentication for that request.

For a caller-provided bearer token:

```json
{
	"type": "Bearer",
	"tokenProvided": "<replace-with-access-token>"
}
```

For token-endpoint authentication:

```json
{
	"type": "Bearer",
	"credentials": {
		"grantType": "client_credentials",
		"scope": "<scope>",
		"resource": null,
		"tenant": "https://identity.example.com/oauth2/token",
		"clientId": "<client-id>",
		"clientSecret": "<client-secret>",
		"user": "",
		"password": ""
	}
}
```

- `type` is required by `AuthInfoVM`; accepted model values are `Anonymous`, `Basic`, and `Bearer`.
- Prefer omitting `authenticationParams` for anonymous requests. The runtime token flow is bearer-oriented and does not build Basic authentication headers.
- `tokenProvided` and `credentials` are optional, but an authentication object must provide one of them to acquire a token successfully.
- `credentials` is an `HttpTokenParameter`. `grantType` must be `client_credentials` or `password`.
- In `HttpTokenParameter`, `grantType`, `scope`, `tenant`, `clientId`, `clientSecret`, `user`, and `password` are required strings; `resource` is optional and defaults to `null`. Use empty strings for required fields unused by the selected grant.
- Never put real secrets in generated samples. Use explicit replacement placeholders.

## Shared Variables

Define reusable strings in `globalVariables` and reference them with `#{name}#`:

```json
{
	"globalVariables": {
		"baseUrl": "https://api.example.com",
		"accountId": "<account-id>"
	},
	"apiTestRequests": [
		{
			"id": "get-account",
			"url": "#{baseUrl}#/accounts/#{accountId}#",
			"method": "GET"
		}
	]
}
```

Substitution applies to URLs, headers, cookies, query parameters, JSON bodies, response validation paths and values, error messages, and variable definitions. Substituted values become strings. An unknown placeholder remains unchanged.

## Request: `ApiTestRequestVM`

Each item in `apiTestRequests` has this shape:

```json
{
	"id": "get-account",
	"authenticationParams": null,
	"headers": {
		"Accept": "application/json"
	},
	"cookies": null,
	"queryParams": {
		"include": "profile"
	},
	"url": "#{baseUrl}#/accounts/#{accountId}#",
	"method": "GET",
	"jsonBody": null,
	"expectedResponse": {
		"status": 200,
		"contentValidations": {
			"$.id": {
				"type": "equals",
				"value": "#{accountId}#",
				"errorMessage": "The returned account id did not match"
			}
		}
	},
	"variables": {
		"accountName": "$.name"
	},
	"waitForEventPropagation": null
}
```

- Required fields: `id`, `url`, and `method`.
- Optional fields: `authenticationParams`, `headers`, `cookies`, `queryParams`, `jsonBody`, `expectedResponse`, `variables`, `waitForEventPropagation`, and `referenceFile`.
- `headers`, `cookies`, and `queryParams` are string-to-string objects.
- `jsonBody` is a JSON object and may contain nested values.
- `expectedResponse` defaults to status `200` with no content validations.
- `variables` maps names to JSONPath expressions evaluated against this request's response.
- `waitForEventPropagation` is a string containing a number of seconds to wait after a successful request.
- Omit `referenceFile`; multipart/reference-file handling is not implemented.
- Dynamic placeholders are supported in `jsonBody` and `queryParams`, including `{{DynamicToday}}`, `{{DynamicNow}}`, `{{DynamicFuture}}:<amount><d|h|m>`, `{{DynamicPast}}:<amount><d|h|m>`, `{{DynamicRandomNumber}}:<digits>`, and `{{DynamicRandomGuid}}`.

## Expected Response: `ExpectedResponseVM`

```json
{
	"status": 200,
	"contentValidations": {
		"$.items": {
			"type": "length",
			"value": 2
		}
	}
}
```

- `status` is optional and defaults to `200`.
- `contentValidations` is optional. It maps JSONPath expressions to `ResponseValidationVM` objects.
- Use response schemas and examples from OpenAPI to choose defensible paths and values. Do not guess exact values that the specification does not guarantee.
- A missing token or invalid JSONPath produces a `SelectToken` failure.

## Validation: `ResponseValidationVM`

Each rule requires `type`; `value` and `errorMessage` are optional:

```json
{
	"type": "equals",
	"value": "active",
	"errorMessage": "Expected an active resource"
}
```

Supported types are:

- `fieldnotexists`: succeeds only when the path does not resolve; omit `value`.
- `equals` and `notequals`: compare against `value`.
- `notnull`, `null`, `notempty`, and `empty`: inspect null or empty state; omit `value`.
- `contains` and `notcontains`: check a string or list against `value`.
- `containsall`: requires an array in `value` and an array at the JSONPath.
- `containspropertywithvalue`: requires a one-property object such as `{ "status": "active" }` and an array of objects at the JSONPath.
- `length`: compares the length of a string, object, or array with `value`.

## Extracting Values Between Requests

Request-level `variables` store the first JSONPath match and merge it into `globalVariables` for later requests:

```json
{
	"id": "create-account",
	"url": "#{baseUrl}#/accounts",
	"method": "POST",
	"jsonBody": {
		"name": "Sample account"
	},
	"expectedResponse": {
		"status": 201
	},
	"variables": {
		"createdAccountId": "$.id"
	}
}
```

A later request can use `#{createdAccountId}#`. A missing extraction path is a validation failure, so only extract fields guaranteed by the documented response.

## Generation Rules

- Derive methods, paths, parameters, request bodies, security, status codes, and response fields from the target operation's OpenAPI definition.
- Prefer one focused sample file per meaningful operation or scenario.
- Put path parameters into the URL, query parameters into `queryParams`, headers into `headers`, and JSON request bodies into `jsonBody`.
- Use `globalVariables` for the server base URL and values shared by multiple requests.
- Include only validations justified by the documented response schema or examples.
- Keep required-but-unknown inputs as obvious `<replace-me>` placeholders.
- Ensure every generated root object contains both `globalVariables` and `apiTestRequests`.
