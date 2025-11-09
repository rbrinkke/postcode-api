"""
Mock Database Pool

Drop-in replacement for DatabasePool for unit testing.
Provides mock database connections and query execution without SQLite.
"""

from typing import Dict, List, Any, Optional
import asyncio


class MockDatabasePool:
    """
    Mock DatabasePool for unit testing.

    Simulates database connection and query execution
    without requiring actual SQLite database.

    Usage:
        >>> db = MockDatabasePool()
        >>> db.set_mock_result("unilabel", [{"postcode": "1012AB", ...}])
        >>> result = await db.execute_query("SELECT * FROM unilabel WHERE postcode = ?", ("1012AB",))
    """

    def __init__(self):
        """Initialize mock database pool"""
        self.is_connected = True
        self.query_count = 0
        self.mock_results: Dict[str, List[Dict]] = {}
        self.query_history: List[Dict] = []
        self.should_raise_error = False
        self.error_message = "Mock database error"
        self.connection_delay_ms = 0

    async def connect(self) -> None:
        """Mock database connection"""
        if self.connection_delay_ms > 0:
            await asyncio.sleep(self.connection_delay_ms / 1000.0)

        if not self.is_connected:
            raise Exception("Database connection failed (mock)")

    async def disconnect(self) -> None:
        """Mock database disconnection"""
        self.is_connected = False

    async def execute_query(
        self, query: str, params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Execute mock query and return predefined results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result dictionaries

        Raises:
            Exception: If error mode is enabled
        """
        self.query_count += 1

        # Record query in history
        self.query_history.append(
            {"query": query, "params": params, "count": self.query_count}
        )

        # Simulate error if configured
        if self.should_raise_error:
            raise Exception(self.error_message)

        # Parse query to determine what data to return
        if "unilabel" in query.lower():
            if params:
                postcode = params[0]
                return self._mock_postcode_lookup(postcode)
            else:
                # Return all mock postcodes
                return self.mock_results.get("unilabel_all", [])

        # Check for specific table results
        for table_name, results in self.mock_results.items():
            if table_name.lower() in query.lower():
                return results

        return []

    def _mock_postcode_lookup(self, postcode: str) -> List[Dict[str, Any]]:
        """
        Mock postcode lookup query.

        Args:
            postcode: Postcode to look up

        Returns:
            List with single result or empty list
        """
        unilabel_data = self.mock_results.get("unilabel", [])

        for row in unilabel_data:
            if row.get("postcode") == postcode:
                return [row]

        return []

    async def health_check(self) -> bool:
        """
        Mock health check.

        Returns:
            True if connected, False otherwise
        """
        if self.should_raise_error:
            return False

        return self.is_connected

    def set_mock_result(self, table_name: str, results: List[Dict]) -> None:
        """
        Configure mock query results.

        Args:
            table_name: Table name or query identifier
            results: List of result dictionaries
        """
        self.mock_results[table_name] = results

    def add_mock_postcode(
        self, postcode: str, lat: float, lon: float, woonplaats: str
    ) -> None:
        """
        Add mock postcode to unilabel table results.

        Args:
            postcode: Postcode
            lat: Latitude
            lon: Longitude
            woonplaats: City name
        """
        if "unilabel" not in self.mock_results:
            self.mock_results["unilabel"] = []

        self.mock_results["unilabel"].append(
            {"postcode": postcode, "lat": lat, "lon": lon, "woonplaats": woonplaats}
        )

    def simulate_disconnection(self) -> None:
        """Simulate database disconnection"""
        self.is_connected = False

    def simulate_reconnection(self) -> None:
        """Simulate database reconnection"""
        self.is_connected = True

    def set_error_mode(
        self, should_error: bool, message: str = "Database error"
    ) -> None:
        """
        Configure database to raise errors.

        Args:
            should_error: Whether to raise errors on queries
            message: Error message to use
        """
        self.should_raise_error = should_error
        self.error_message = message

    def set_connection_delay(self, delay_ms: int) -> None:
        """
        Set artificial connection delay.

        Args:
            delay_ms: Delay in milliseconds
        """
        self.connection_delay_ms = delay_ms

    def clear_query_history(self) -> None:
        """Clear query history"""
        self.query_history.clear()

    def get_query_history(self) -> List[Dict]:
        """
        Get list of all executed queries.

        Returns:
            List of query dictionaries
        """
        return self.query_history.copy()

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database stats
        """
        return {
            "is_connected": self.is_connected,
            "query_count": self.query_count,
            "tables_configured": list(self.mock_results.keys()),
            "total_rows": sum(len(rows) for rows in self.mock_results.values()),
            "error_mode": self.should_raise_error,
        }

    def reset(self) -> None:
        """Reset database to initial state"""
        self.is_connected = True
        self.query_count = 0
        self.mock_results.clear()
        self.query_history.clear()
        self.should_raise_error = False


def create_mock_database_with_postcodes(postcodes: List[Dict]) -> MockDatabasePool:
    """
    Create mock database pre-populated with postcode data.

    Args:
        postcodes: List of postcode dictionaries

    Returns:
        MockDatabasePool with postcode data
    """
    db = MockDatabasePool()
    db.set_mock_result("unilabel", postcodes)
    return db
