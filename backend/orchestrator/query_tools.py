from langchain.tools import BaseTool
from orchestrator.utils import post_to_level

class QueryTool(BaseTool):
    name: str
    level_url: str
    description: str

    def _run(self, query: str, top_k: int = None, max_output_tokens: int = 512):
        payload = {"question": query, "top_k": top_k, "max_output_tokens": max_output_tokens}
        return post_to_level(self.level_url, "/query", json=payload)

    async def _arun(self, query: str, top_k: int = None, max_output_tokens: int = 512):
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, query, top_k, max_output_tokens)
