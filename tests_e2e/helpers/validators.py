"""
Response validators for E2E tests
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class ResponseValidator:
    """Validate API responses match expected structures"""

    @staticmethod
    def validate_auth_token_response(response: Dict[str, Any]) -> bool:
        """Validate authentication token response structure"""
        required_fields = ["access_token", "token_type", "expires_in"]

        # Check required fields
        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types
        assert isinstance(response["access_token"], str), "access_token must be a string"
        assert response["token_type"] == "Bearer", "token_type must be 'Bearer'"
        assert isinstance(response["expires_in"], int), "expires_in must be an integer"
        assert response["expires_in"] > 0, "expires_in must be positive"

        # Refresh token is optional but if present, must be string
        if "refresh_token" in response:
            assert isinstance(response["refresh_token"], str), "refresh_token must be a string"

        return True

    @staticmethod
    def validate_user_response(response: Dict[str, Any]) -> bool:
        """Validate user response structure"""
        required_fields = ["id", "email", "name", "created_at", "updated_at"]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types and formats
        assert isinstance(response["id"], str), "id must be a string"
        assert ResponseValidator.is_valid_email(response["email"]), "Invalid email format"
        assert isinstance(response["name"], str), "name must be a string"
        assert ResponseValidator.is_valid_datetime(response["created_at"]), "Invalid created_at datetime"
        assert ResponseValidator.is_valid_datetime(response["updated_at"]), "Invalid updated_at datetime"

        return True

    @staticmethod
    def validate_account_response(response: Dict[str, Any]) -> bool:
        """Validate account response structure"""
        required_fields = ["id", "user_id", "name", "broker", "account_number", "is_active", "created_at", "updated_at"]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types
        assert isinstance(response["id"], str), "id must be a string"
        assert isinstance(response["user_id"], str), "user_id must be a string"
        assert isinstance(response["name"], str), "name must be a string"
        assert isinstance(response["broker"], str), "broker must be a string"
        assert isinstance(response["account_number"], str), "account_number must be a string"
        assert isinstance(response["is_active"], bool), "is_active must be a boolean"
        assert ResponseValidator.is_valid_datetime(response["created_at"]), "Invalid created_at datetime"
        assert ResponseValidator.is_valid_datetime(response["updated_at"]), "Invalid updated_at datetime"

        return True

    @staticmethod
    def validate_asset_response(response: Dict[str, Any]) -> bool:
        """Validate asset response structure"""
        required_fields = ["id", "ticker", "name", "type", "created_at", "updated_at"]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types
        assert isinstance(response["id"], str), "id must be a string"
        assert isinstance(response["ticker"], str), "ticker must be a string"
        assert len(response["ticker"]) > 0, "ticker cannot be empty"
        assert isinstance(response["name"], str), "name must be a string"
        assert response["type"] in ["STOCK", "ETF", "FII", "BDR"], f"Invalid asset type: {response['type']}"
        assert ResponseValidator.is_valid_datetime(response["created_at"]), "Invalid created_at datetime"
        assert ResponseValidator.is_valid_datetime(response["updated_at"]), "Invalid updated_at datetime"

        return True

    @staticmethod
    def validate_option_response(response: Dict[str, Any]) -> bool:
        """Validate option response structure"""
        required_fields = [
            "id", "account_id", "asset_id", "ticker", "strike",
            "expiry", "side", "strategy", "quantity", "entry_price",
            "status", "created_at", "updated_at"
        ]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types and values
        assert isinstance(response["id"], str), "id must be a string"
        assert isinstance(response["account_id"], str), "account_id must be a string"
        assert isinstance(response["asset_id"], str), "asset_id must be a string"
        assert isinstance(response["ticker"], str), "ticker must be a string"
        assert isinstance(response["strike"], (int, float)), "strike must be a number"
        assert response["strike"] > 0, "strike must be positive"
        assert ResponseValidator.is_valid_date(response["expiry"]), "Invalid expiry date format"
        assert response["side"] in ["CALL", "PUT"], f"Invalid option side: {response['side']}"
        assert response["strategy"] in ["COVERED_CALL", "SHORT_PUT", "LONG_PUT", "LONG_CALL", "OTHER"], f"Invalid strategy: {response['strategy']}"
        assert isinstance(response["quantity"], int), "quantity must be an integer"
        assert response["quantity"] != 0, "quantity cannot be zero"
        assert isinstance(response["entry_price"], (int, float)), "entry_price must be a number"
        assert response["entry_price"] >= 0, "entry_price cannot be negative"
        assert response["status"] in ["OPEN", "CLOSED", "EXPIRED", "EXERCISED", "ASSIGNED"], f"Invalid status: {response['status']}"

        return True

    @staticmethod
    def validate_rule_response(response: Dict[str, Any]) -> bool:
        """Validate rule response structure"""
        required_fields = [
            "id", "user_id", "name", "description", "condition_type",
            "threshold", "is_active", "created_at", "updated_at"
        ]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types
        assert isinstance(response["id"], str), "id must be a string"
        assert isinstance(response["user_id"], str), "user_id must be a string"
        assert isinstance(response["name"], str), "name must be a string"
        assert isinstance(response["description"], str), "description must be a string"
        assert isinstance(response["condition_type"], str), "condition_type must be a string"
        assert isinstance(response["threshold"], (int, float)), "threshold must be a number"
        assert isinstance(response["is_active"], bool), "is_active must be a boolean"

        return True

    @staticmethod
    def validate_alert_response(response: Dict[str, Any]) -> bool:
        """Validate alert response structure"""
        required_fields = ["id", "rule_id", "triggered_at", "message", "status", "created_at"]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        # Validate field types
        assert isinstance(response["id"], str), "id must be a string"
        assert isinstance(response["rule_id"], str), "rule_id must be a string"
        assert ResponseValidator.is_valid_datetime(response["triggered_at"]), "Invalid triggered_at datetime"
        assert isinstance(response["message"], str), "message must be a string"
        assert response["status"] in ["PENDING", "PROCESSING", "SENT", "FAILED", "ACKNOWLEDGED"], f"Invalid status: {response['status']}"

        return True

    @staticmethod
    def validate_error_response(response: Dict[str, Any], expected_status: Optional[int] = None) -> bool:
        """Validate error response structure"""
        # Error responses should have either 'error' or 'detail' field
        assert "error" in response or "detail" in response, "Error response must contain 'error' or 'detail' field"

        if "error" in response:
            assert isinstance(response["error"], str), "error must be a string"

        if "detail" in response:
            assert isinstance(response["detail"], (str, list, dict)), "detail must be a string, list, or dict"

        if expected_status and "status" in response:
            assert response["status"] == expected_status, f"Expected status {expected_status}, got {response['status']}"

        return True

    @staticmethod
    def validate_pagination_response(response: Dict[str, Any]) -> bool:
        """Validate paginated response structure"""
        required_fields = ["items", "total", "page", "per_page", "pages"]

        for field in required_fields:
            if field not in response:
                raise AssertionError(f"Missing required field: {field}")

        assert isinstance(response["items"], list), "items must be a list"
        assert isinstance(response["total"], int), "total must be an integer"
        assert isinstance(response["page"], int), "page must be an integer"
        assert isinstance(response["per_page"], int), "per_page must be an integer"
        assert isinstance(response["pages"], int), "pages must be an integer"

        # Validate pagination logic
        assert response["page"] > 0, "page must be positive"
        assert response["per_page"] > 0, "per_page must be positive"
        assert response["pages"] >= 0, "pages cannot be negative"
        assert len(response["items"]) <= response["per_page"], "items count cannot exceed per_page"

        return True

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_datetime(datetime_str: str) -> bool:
        """Validate datetime string format (ISO 8601)"""
        try:
            datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True
        except:
            return False

    @staticmethod
    def is_valid_date(date_str: str) -> bool:
        """Validate date string format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except:
            return False

    @staticmethod
    def validate_list_response(response: List[Any], item_validator: callable) -> bool:
        """Validate a list response where each item should match a validator"""
        assert isinstance(response, list), "Response must be a list"

        for item in response:
            item_validator(item)

        return True

    @staticmethod
    def validate_success_message(response: Dict[str, Any], expected_message: Optional[str] = None) -> bool:
        """Validate success message response"""
        assert "message" in response or "success" in response, "Success response must contain 'message' or 'success' field"

        if "message" in response:
            assert isinstance(response["message"], str), "message must be a string"
            if expected_message:
                assert expected_message in response["message"], f"Expected message to contain '{expected_message}'"

        if "success" in response:
            assert isinstance(response["success"], bool), "success must be a boolean"
            assert response["success"] is True, "success must be True"

        return True