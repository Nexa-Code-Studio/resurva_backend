import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIFactory


class ChatSummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summarize_conversation(self, conversation_id: uuid.UUID, messages: list) -> str:
        """
        Summarizes chat messages using the LLM Provider Factory to create a concise title.
        """
        if not messages:
            return "Percakapan Baru"

        text_content = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt = f"Buat judul chat singkat (maksimal 4 kata) dalam Bahasa Indonesia untuk riwayat percakapan berikut:\n\n{text_content}"

        try:
            llm = AIFactory.get_llm_provider()
            system_prompt = (
                "Kamu adalah bot pembuat judul percakapan chat. "
                "Tugasmu adalah membuat judul singkat (maksimal 4 kata) dalam Bahasa Indonesia yang meringkas topik obrolan. "
                "JANGAN gunakan tanda kutip, jangan gunakan titik di akhir, dan buat sepadat mungkin (contoh: 'Stok Muffin Blueberry' atau 'Analisis Penjualan Toko')."
            )
            summary = await llm.generate_response(prompt, system_prompt=system_prompt)
            # Remove enclosing quotes if any
            clean_summary = summary.strip().strip('"').strip("'").strip("`").strip(".")
            return clean_summary
        except Exception:
            # Simple fallback based on the first user message if available
            user_msgs = [m for m in messages if m["role"] == "user"]
            if user_msgs:
                first_content = user_msgs[0]["content"]
                return first_content[:25] + "..." if len(first_content) > 25 else first_content
            return "Percakapan Baru"

