"""
Postcode API Mock Client Example

Demonstrates how to interact with the mock server using Python.

Usage:
    python mocks/examples/python_client.py

Requirements:
    pip install httpx
"""

import asyncio
import httpx
from typing import Optional, Dict


class PostcodeMockClient:
    """Client for interacting with Postcode API mock server"""

    def __init__(self, base_url: str = "http://localhost:8888"):
        """
        Initialize client.

        Args:
            base_url: Base URL of mock server
        """
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    async def lookup_postcode(
        self,
        postcode: str,
        simulate_error: Optional[str] = None,
        delay_ms: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Look up postcode.

        Args:
            postcode: Dutch postcode (e.g., "1012AB")
            simulate_error: Optional error to simulate (404, 500, 503)
            delay_ms: Optional delay in milliseconds

        Returns:
            Postcode data or None if not found

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        params = {}
        if simulate_error:
            params["simulate_error"] = simulate_error
        if delay_ms:
            params["delay_ms"] = delay_ms

        response = await self.client.get(f"/postcode/{postcode}", params=params)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    async def health_check(self) -> Dict:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def get_stats(self) -> Dict:
        """
        Get mock server statistics.

        Returns:
            Statistics dictionary
        """
        response = await self.client.get("/mock/stats")
        response.raise_for_status()
        return response.json()

    async def get_config(self) -> Dict:
        """
        Get mock server configuration.

        Returns:
            Configuration dictionary
        """
        response = await self.client.get("/mock/config")
        response.raise_for_status()
        return response.json()

    async def list_postcodes(self, limit: int = 100) -> Dict:
        """
        List available postcodes.

        Args:
            limit: Maximum postcodes to return

        Returns:
            Dictionary with postcode list
        """
        response = await self.client.get("/mock/data", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    async def enable_errors(self, error_rate: float = 0.05) -> Dict:
        """
        Enable error simulation.

        Args:
            error_rate: Error rate (0.0 to 1.0)

        Returns:
            Configuration result
        """
        response = await self.client.post(
            "/mock/errors/enable", params={"error_rate": error_rate}
        )
        response.raise_for_status()
        return response.json()

    async def disable_errors(self) -> Dict:
        """
        Disable error simulation.

        Returns:
            Configuration result
        """
        response = await self.client.post("/mock/errors/disable")
        response.raise_for_status()
        return response.json()

    async def set_delay(self, min_ms: int, max_ms: int) -> Dict:
        """
        Configure response delay.

        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds

        Returns:
            Configuration result
        """
        response = await self.client.post(
            "/mock/delay/set", params={"min_ms": min_ms, "max_ms": max_ms}
        )
        response.raise_for_status()
        return response.json()

    async def disable_delay(self) -> Dict:
        """
        Disable response delay.

        Returns:
            Configuration result
        """
        response = await self.client.post("/mock/delay/disable")
        response.raise_for_status()
        return response.json()

    async def reload_data(self) -> Dict:
        """
        Reload mock data from fixtures.

        Returns:
            Reload result
        """
        response = await self.client.post("/mock/data/reload")
        response.raise_for_status()
        return response.json()

    async def generate_data(self, count: int) -> Dict:
        """
        Generate additional mock postcodes.

        Args:
            count: Number of postcodes to generate

        Returns:
            Generation result
        """
        response = await self.client.post(
            "/mock/data/generate", params={"count": count}
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Example Usage
# ============================================================================


async def main():
    """Example usage of the PostcodeMockClient"""

    print("=" * 60)
    print("Postcode API Mock Client - Python Example")
    print("=" * 60)
    print()

    async with PostcodeMockClient() as client:
        # Example 1: Basic postcode lookup
        print("1. Basic Postcode Lookup")
        print("-" * 60)
        result = await client.lookup_postcode("1012AB")
        if result:
            print(f"  Postcode: {result['postcode']}")
            print(f"  City: {result['woonplaats']}")
            print(f"  Coordinates: {result['lat']}, {result['lon']}")
        else:
            print("  Postcode not found")
        print()

        # Example 2: Health check
        print("2. Health Check")
        print("-" * 60)
        health = await client.health_check()
        print(f"  Status: {health['status']}")
        print(f"  Database: {health['database']}")
        print()

        # Example 3: Get statistics
        print("3. Server Statistics")
        print("-" * 60)
        stats = await client.get_stats()
        server_stats = stats["server"]
        print(f"  Total Requests: {server_stats['total_requests']}")
        print(f"  Success Rate: {server_stats['success_rate']:.2%}")
        print(f"  Avg Response Time: {server_stats['average_response_time_ms']:.2f}ms")
        print()

        # Example 4: List postcodes
        print("4. List Available Postcodes (first 10)")
        print("-" * 60)
        postcodes = await client.list_postcodes(limit=10)
        print(f"  Total Available: {postcodes['total_count']}")
        print(f"  First 10: {', '.join(postcodes['postcodes'][:10])}")
        print()

        # Example 5: Test error simulation
        print("5. Error Simulation")
        print("-" * 60)
        try:
            await client.lookup_postcode("1012AB", simulate_error="404")
            print("  ✗ Expected 404 error but got success!")
        except httpx.HTTPStatusError as e:
            print(f"  ✓ Successfully simulated 404 error")
        print()

        # Example 6: Test delay simulation
        print("6. Delay Simulation")
        print("-" * 60)
        import time

        start = time.time()
        await client.lookup_postcode("1012AB", delay_ms=500)
        duration = (time.time() - start) * 1000
        print(f"  Request with 500ms delay took {duration:.0f}ms")
        print()

        # Example 7: Enable/disable error simulation
        print("7. Control Error Simulation")
        print("-" * 60)
        await client.enable_errors(error_rate=0.1)
        print("  ✓ Enabled error simulation (10% rate)")

        # Make multiple requests to see random errors
        successes = 0
        failures = 0
        for i in range(10):
            try:
                await client.lookup_postcode("1012AB")
                successes += 1
            except httpx.HTTPStatusError:
                failures += 1

        print(f"  Made 10 requests: {successes} succeeded, {failures} failed")

        await client.disable_errors()
        print("  ✓ Disabled error simulation")
        print()

        # Example 8: Generate additional data
        print("8. Generate Additional Data")
        print("-" * 60)
        result = await client.generate_data(count=50)
        print(f"  Generated {result['count']} postcodes")
        print(f"  Total postcodes: {result['total_postcodes']}")
        print()

        # Example 9: Batch lookups
        print("9. Batch Lookups")
        print("-" * 60)
        test_postcodes = ["1012AB", "3011AA", "3511AA", "2511AA", "9999ZZ"]
        results = []

        for pc in test_postcodes:
            try:
                data = await client.lookup_postcode(pc)
                if data:
                    results.append(f"{pc} → {data['woonplaats']}")
                else:
                    results.append(f"{pc} → Not found")
            except httpx.HTTPStatusError as e:
                results.append(f"{pc} → Error {e.response.status_code}")

        for result in results:
            print(f"  {result}")
        print()

        # Example 10: Configuration
        print("10. Server Configuration")
        print("-" * 60)
        config = await client.get_config()
        print(f"  Port: {config['mock_port']}")
        print(f"  Data Size: {config['mock_data_size']}")
        print(f"  Error Simulation: {config['error_simulation_enabled']}")
        print(f"  Response Delay: {config['enable_response_delay']}")
        print()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
