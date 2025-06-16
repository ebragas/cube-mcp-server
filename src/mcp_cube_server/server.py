from __future__ import annotations
from typing import Annotated, Any, Literal, Optional, Union
from pydantic import ConfigDict
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, EmbeddedResource, TextResourceContents
import jwt
from pydantic import BaseModel, Field
import requests
import json
import logging
import yaml
import uuid
import time


def data_to_yaml(data: Any) -> str:
    return yaml.dump(data, indent=2, sort_keys=False)


class CubeClient:
    Route = Literal["meta", "load"]
    max_wait_time = 10
    request_backoff = 1
    request_timeout = 30  # seconds

    def __init__(self, endpoint: str, api_secret: str, token_payload: dict, logger: logging.Logger):
        self.endpoint = endpoint
        self.api_secret = api_secret
        self.token_payload = token_payload
        self.token = None
        self.logger = logger
        self.is_pregenerated_token = self._detect_pregenerated_token()
        self._refresh_token()
        self.meta = self.describe()

    def _detect_pregenerated_token(self):
        """Detect if api_secret is actually a pre-generated JWT token"""
        return len(self.api_secret.split('.')) == 3 and all(
            part for part in self.api_secret.split('.')
        )

    def _generate_token(self):
        if self.is_pregenerated_token:
            # Use the pre-generated token directly
            return self.api_secret
        else:
            # Generate JWT with proper claims
            payload = dict(self.token_payload)
            payload['iat'] = int(time.time())
            payload['exp'] = int(time.time()) + 3600  # 1 hour expiration
            return jwt.encode(payload, self.api_secret, algorithm="HS256")

    def _sanitize_headers(self, headers: dict) -> dict:
        """Sanitize headers by redacting Authorization token for safe logging"""
        sanitized = headers.copy()
        if 'Authorization' in sanitized:
            sanitized['Authorization'] = '[REDACTED]'
        return sanitized

    def _sanitize_response_for_logging(self, response: dict) -> dict:
        """Sanitize response data for safe logging"""
        sanitized = response.copy()
        
        # Redact or truncate large data arrays to prevent sensitive data exposure
        if 'data' in sanitized and sanitized['data']:
            data_size = len(sanitized['data'])
            if data_size > 0:
                # Always truncate data for security - only show count and structure info
                sanitized['data'] = f"[DATA REDACTED - {data_size} rows]"
        
        # Redact any other potentially sensitive fields
        sensitive_fields = ['token', 'secret', 'key', 'password', 'auth']
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '[REDACTED]'
        
        # Truncate very long string values that might contain sensitive data
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:200] + f"... [TRUNCATED - original length: {len(value)}]"
        
        return sanitized

    def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token structure and basic claims without verifying signature"""
        if not token:
            return False
        
        try:
            # For pre-generated tokens, do basic structure validation
            if self.is_pregenerated_token:
                parts = token.split('.')
                return len(parts) == 3 and all(part for part in parts)
            
            # For generated tokens, decode without verification to check structure
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Check required claims
            required_claims = ['iat', 'exp']
            if not all(claim in decoded for claim in required_claims):
                return False
                
            # Check token expiration
            exp_claim = decoded.get('exp')
            if exp_claim is None or exp_claim < time.time():
                return False
                
            return True
            
        except Exception as e:
            self.logger.warning(f"JWT token validation failed: {str(e)}")
            return False

    def _refresh_token(self):
        new_token = self._generate_token()
        
        # Validate the token before using it
        if not self._validate_jwt_token(new_token):
            self.logger.error("Generated token failed validation")
            raise ValueError("Invalid token generated")
            
        self.token = new_token
        self.logger.debug("Token refreshed successfully")

    def _request(self, route: Route, **params):
        request_time = time.time()
        headers = {"Authorization": self.token}
        url = f"{self.endpoint if self.endpoint[-1] != '/' else self.endpoint[:-1]}/{route}"
        serialized_params = {k: json.dumps(v) for k, v in params.items()}

        # Log request details with sanitized headers
        sanitized_headers = self._sanitize_headers(headers)
        self.logger.debug(f"Making request to {url} with headers: {sanitized_headers}")

        try:
            response = requests.get(url, headers=headers, params=serialized_params, timeout=self.request_timeout)

            # Handle "continue wait" responses
            while response.json().get("error") == "Continue wait":
                if time.time() - request_time > self.max_wait_time:
                    self.logger.error(f"Request timed out after {self.max_wait_time} seconds")
                    return {"error": "Request timed out. Something may have gone wrong or the request may be too complex."}
                self.logger.warning(f"Request incomplete, polling again in {self.request_backoff} second(s)")
                time.sleep(self.request_backoff)
                response = requests.get(url, headers=headers, params=serialized_params, timeout=self.request_timeout)

            # Handle 403 responses by trying to refresh the token once
            if response.status_code == 403:
                if self.is_pregenerated_token:
                    self.logger.error("Authentication failed with pre-generated token")
                    return {"error": "Authentication failed. Please check your API token."}
                else:
                    self.logger.warning("Received 403, attempting token refresh")
                    self._refresh_token()
                    headers = {"Authorization": self.token}  # Update headers with new token
                    
                    # Log retry request with sanitized headers
                    sanitized_headers = self._sanitize_headers(headers)
                    self.logger.debug(f"Retrying request with refreshed token: {sanitized_headers}")
                    
                    response = requests.get(url, headers=headers, params=serialized_params, timeout=self.request_timeout)
                    return response.json()

            if response.status_code != 200:
                self.logger.error(f"Request failed with error: {str(response.json().get('error'))}")

            return response.json()

        except Exception as e:
            self.logger.error(f"Request failed with error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}

    def describe(self):
        return self._request("meta")

    def _cast_numerics(self, response):
        if response.get("data") and response.get("annotation"):
            # Find which keys are numeric
            numeric_keys = set()
            dimensions_and_measures = dict(
                response["annotation"].get("dimensions", {}), **response["annotation"].get("measures", [])
            )
            for column_name, column in dimensions_and_measures.items():
                if column.get("type") == "number":
                    numeric_keys.add(column_name)
            # Cast numeric values to numbers
            for row in response["data"]:
                for key in numeric_keys:
                    try:
                        row[key] = float(row[key])
                        if row[key].is_integer():
                            row[key] = int(row[key])
                    except (ValueError, TypeError):
                        pass
        return response

    def query(self, query, cast_numerics=True):
        response = self._request("load", query=query)
        if cast_numerics:
            response = self._cast_numerics(response)
        return response


class TimeDimension(BaseModel):
    dimension: str = Field(..., description="Name of the time dimension")
    granularity: Literal["second", "minute", "hour", "day", "week", "month", "quarter", "year"] = Field(
        ..., description="Time granularity"
    )
    dateRange: Union[list[str], str] = Field(
        ...,
        description="Pair of dates ISO dates representing the start and end of the range. Alternatively, a string representing a relative date range of the form: 'last N days', 'today', 'yesterday', 'last year', etc.",
    )

    model_config = ConfigDict()


class Query(BaseModel):

    measures: list[str] = Field([], description="Names of measures to query")
    dimensions: list[str] = Field([], description="Names of dimensions to group by")
    timeDimensions: list[TimeDimension] = Field([], description="Time dimensions to group by")
    # filters: list[TimeDimension] = Field([], description="Filters to apply to the query")  # TODO: Implement filters using TimeDimension structure or create dedicated Filter class if needed
    limit: Optional[int] = Field(500, description="Maximum number of rows to return. Defaults to 500")
    offset: Optional[int] = Field(0, description="Number of rows to skip. Defaults to 0")
    order: dict[str, Literal["asc", "desc"]] = Field(
        {}, description="Optional ordering of the results. The order is sensitive to the order of keys."
    )
    ungrouped: bool = Field(
        False,
        description="Return results without grouping by dimensions. Instead, return all rows. This can be useful for fetching a single row by its ID as well.",
    )

    model_config = ConfigDict()


def main(credentials, logger):
    mcp = FastMCP("Cube.dev")

    client = CubeClient(**credentials, logger=logger)

    @mcp.resource("context://data_description")
    def data_description() -> str:
        """Describe the data available in Cube."""
        meta = client.describe()
        if error := meta.get("error"):
            logger.error("Error in data_description: %s\n\n%s", error, meta.get("stack"))
            logger.error("Full response: %s", json.dumps(client._sanitize_response_for_logging(meta)))
            return f"Error: Description of the data is not available: {error}, {meta}"

        description = []
        for cube in meta.get("cubes", []):
            if isinstance(cube, dict):
                description.append({
                    "name": cube.get("name"),
                    "title": cube.get("title"),
                    "description": cube.get("description"),
                    "dimensions": [
                        {
                            "name": dimension.get("name"),
                            "title": dimension.get("shortTitle") or dimension.get("title"),
                            "description": dimension.get("description"),
                        }
                        for dimension in cube.get("dimensions", [])
                        if isinstance(dimension, dict)
                    ],
                    "measures": [
                        {
                            "name": measure.get("name"),
                            "title": measure.get("shortTitle") or measure.get("title"),
                            "description": measure.get("description"),
                        }
                        for measure in cube.get("measures", [])
                        if isinstance(measure, dict)
                    ],
                })
        return "Here is a description of the data available via the read_data tool:\n\n" + yaml.dump(
            description, indent=2, sort_keys=True
        )

    @mcp.tool("describe_data")
    def describe_data() -> dict[str, str]:
        """Describe the data available in Cube."""
        return {"type": "text", "text": data_description()}

    @mcp.tool("read_data")
    def read_data(query: Query) -> Union[str, list[Union[TextContent, EmbeddedResource]]]:
        """Read data from Cube."""
        try:
            query_dict = query.model_dump(by_alias=True, exclude_none=True)
            logger.info("read_data called with query: %s", json.dumps(query_dict))
            response = client.query(query_dict)
            if error := response.get("error"):
                logger.error("Error in read_data: %s\n\n%s", error, response.get("stack"))
                logger.error("Full response: %s", json.dumps(client._sanitize_response_for_logging(response)))
                return f"Error: {error}"
            data = response.get("data", [])
            logger.info("read_data returned %s rows", len(data))

            data_id = str(uuid.uuid4())

            @mcp.resource(f"data://{data_id}")
            def data_resource() -> str:
                return json.dumps(data)

            logger.info("Added results as resource with ID: %s", data_id)

            output = {
                "type": "data",
                "data_id": data_id,
                "data": data,
            }
            yaml_output = data_to_yaml(output)
            json_output = json.dumps(output)
            return [
                TextContent(type="text", text=yaml_output),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(uri=f"data://{data_id}", text=json_output),  # type: ignore
                ),
            ]

        except Exception as e:
            logger.error("Error in read_data: %s", str(e))
            return f"Error: {str(e)}"

    logger.info("Starting Cube MCP server")
    mcp.run()
