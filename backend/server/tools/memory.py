class MemoryTool:
    name = "memory"
    description = "Search WorkMemory. V0.1 returns an explicit disconnected state."

    def execute(self, **kwargs: object) -> list[str]:
        return []

    def search(self, query: str) -> dict[str, object]:
        return {"status": "not_connected", "query": query, "results": []}
