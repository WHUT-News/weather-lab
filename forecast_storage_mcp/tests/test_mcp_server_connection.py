"""
Quick test to verify MCP server is running and responding.
"""
import asyncio
import httpx


async def test_server():
    """Test if MCP server is reachable."""
    server_url = "http://localhost:8100"

    print(f"Testing connection to MCP server at {server_url}...")

    try:
        async with httpx.AsyncClient() as client:
            print(f"Attempting to connect to {server_url}...")
            # Try to connect to the root endpoint first (simple connectivity test)
            response = await client.get(server_url, timeout=5.0)
            print(f"✅ Server is reachable! Status: {response.status_code}")
            
            # Also check if SSE endpoint exists (HEAD request to avoid timeout)
            sse_response = await client.head(f"{server_url}/sse", timeout=5.0)
            print(f"✅ SSE endpoint available! Status: {sse_response.status_code}")
            return True
    except httpx.ConnectError as e:
        print(f"❌ Cannot connect to server at {server_url}")
        print(f"   Connection error details: {e}")
        print("   Make sure the MCP server is running:")
        print("   cd forecast_storage_mcp && MCP_TRANSPORT=http PORT=8100 python server.py")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_server())
