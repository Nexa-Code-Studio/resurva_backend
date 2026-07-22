import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIFactory
from app.ai.interfaces.llm_provider import LLMProvider
from app.core.enums import UserRole
from app.mcp.registry import mcp_registry
from app.modules.users.models import User
from app.modules.business.models import Business
from app.modules.stores.models import Store
from app.modules.chat.service.conversation_service import ConversationService
from app.modules.chat.service.memory_service import MemoryService
from app.modules.chat.service.tool_call_service import ToolCallService, json_serial


MAX_TOOL_TURNS = 5


def build_system_prompt(user: User, slots: dict[str, str] = None, active_skill: str | None = None) -> str:
    base = """Kamu adalah asisten bisnis untuk platform Food Waste Marketplace (Resurva).
Kamu HANYA bisa membaca data dan memberikan rekomendasi. Kamu TIDAK bisa mengubah data apapun.
Selalu jawab dalam Bahasa Indonesia secara ramah dan profesional. Gunakan angka konkret dari data yang tersedia.
Jika data tidak tersedia, katakan dengan jelas dan jangan mengarang.

ATURAN ANTI-HALLUCINATION (WAJIB DIIKUTI TANPA PENGECUALIAN):
- DILARANG KERAS menyebutkan nama produk, jumlah stok, harga, atau data bisnis apapun SEBELUM memanggil tool yang sesuai dan mendapatkan hasilnya.
- Data produk HARUS SELALU diambil dari hasil tool call. JANGAN pernah menebak, mengasumsikan, atau mengarang nama produk berdasarkan nama toko, kategori bisnis, atau konteks percakapan apapun.
- Contoh SALAH: Toko bernama "Catering Mpok Siti" → AI langsung menyebut "Nasi Kuning, Nasi Uduk" tanpa memanggil tool. Ini DILARANG.
- Contoh BENAR: Panggil product_search dulu → tunggu hasilnya → baru sebutkan produk berdasarkan data nyata dari tool.
- Jika tidak ada data dari tool, jawab: "Saya belum memiliki data untuk pertanyaan ini. Izinkan saya mencarinya terlebih dahulu." lalu panggil tool yang relevan.

PENTING UNTUK DIINGAT:
- Jika pengguna menanyakan detail produk (seperti stok, rekomendasi produksi, audit, atau peringatan kedaluwarsa) berdasarkan namanya, kamu WAJIB mencari produk tersebut terlebih dahulu menggunakan tool 'product_search' untuk mendapatkan 'id' (UUID) produk yang valid. JANGAN PERNAH memberikan string nama produk mentah (seperti "muffin-blueberry") sebagai argumen 'product_id' ke tool lain yang memerlukan UUID.
- Jika pengguna bertanya mengenai total produk atau ingin melihat seluruh daftar produk di toko, panggil tool 'product_search' dengan mengosongkan/tidak mengirimkan argumen 'query' (tapi wajib mengisi 'store_id') dan pastikan 'include_out_of_stock' bernilai true. Gunakan nilai 'total_count' dari hasil kembalian untuk menyebutkan total produk secara akurat.
- Jika pemanggilan tool pencarian produk (product_search) mengembalikan lebih dari satu hasil produk yang mirip, kamu WAJIB menyajikan seluruh daftar produk tersebut (beserta confidence score / skor kecocokannya jika relevan) kepada pengguna.
- Tanyakan secara ramah dan jelas mana produk yang mereka maksudkan.
- JANGAN melanjutkan analisis atau memanggil tool operasional lainnya (seperti mengecek stok atau rincian batch kedaluwarsa) untuk salah satu produk secara sembarangan sebelum pengguna memberikan klarifikasi dan memilih produk yang mereka inginkan secara eksplisit.
- JANGAN PERNAH menampilkan, menyebutkan, atau membocorkan ID database apapun secara eksplisit kepada pengguna dalam jawaban Anda (seperti store_id, business_id, product_id, user_id, dll. yang berformat UUID atau angka). ID database tersebut hanya boleh digunakan secara internal saat memanggil MCP tools. Selalu sebutkan nama toko atau nama produk secara langsung sebagai gantinya (misal: gunakan nama toko 'Sentosa Bakery - Tebet' daripada menuliskan store_id-nya).

INFORMASI FORMULA AUDIT / KESEHATAN PRODUK (PRODUCT HEALTH/AUDIT):
Jika pengguna bertanya mengenai dari mana skor kesehatan/audit produk berasal, bagaimana rumusnya, bobot komponennya, atau interpretasi statusnya, jawab dengan tepat sesuai ketentuan berikut:
1. Skor Kesehatan/Audit dihitung dari skala 0-100 menggunakan gabungan 3 komponen utama:
   - Volume Penjualan (Sales Volume) dengan bobot 40%. Dihitung dari penjualan produk tersebut dinormalisasi terhadap penjualan produk terlaris di toko tersebut (sold / max_sales * 100).
   - Rating Pelanggan (Customer Ratings) dengan bobot 30%. Dihitung dari rata-rata rating ulasan pelanggan (avg_rating / 5.0 * 100). Jika belum ada ulasan, sistem menggunakan rata-rata rating toko sebagai fallback.
   - Efisiensi Stok (Stock Efficiency) dengan bobot 30%. Dihitung dari rasio kelebihan stok terhadap rata-rata penjualan harian (overstock_ratio = stock / (avg_daily_sales * 3)). Skor efisiensi dihitung dengan rumus: max(0.0, 100.0 - (overstock_ratio * 50.0)). Jika rata-rata penjualan harian adalah 0, skor efisiensi bernilai 0.0 jika ada stok, dan 100.0 jika tidak ada stok.
2. Status Kelayakan/Kesehatan Produk (Status):
   - Skor >= 70.0: PERFORMING (Sehat, pertahankan produksi dan persediaan saat ini)
   - Skor >= 50.0 dan < 70.0: OPTIMIZE (Perlu optimasi, tinjau harga, buat promosi ringan, atau perbaiki kualitas/review)
   - Skor < 50.0: RETIRE (Kaji ulang / berpotensi dihentikan karena tidak efisien, rating buruk, atau penjualan rendah)"""

    prompt = base

    is_enterprise_user = (
        user.role in (UserRole.OWNER, UserRole.ADMIN)
        or (user.business_id is not None and not user.store_id)
    )

    if is_enterprise_user:
        business_name = user.business.name if user.business else "Bisnis Anda"
        business_id = str(user.business_id) if user.business_id else "tidak diset"
        stores_info = ""
        if user.business and user.business.stores:
            stores_info = ", ".join([f"'{s.name}' (ID: {s.id})" for s in user.business.stores])
        else:
            stores_info = "Belum ada toko terdaftar"
        prompt += (
            f"\n\nKONTEKS: Kamu adalah RESURVA Enterprise AI Assistant yang membantu Manajemen HQ / Owner bisnis '{business_name}' (business_id: {business_id}).\n"
            f"- Cabang/Toko terdaftar ({len(user.business.stores if user.business else [])} toko): {stores_info}.\n"
            "- Kamu HARUS menganalisis performa bisnis secara MAKRO/ENTERPRISE lintas seluruh cabang, bukan hanya 1 toko spesifik.\n"
            "- Fokus pada: perbandingan performa antar cabang, akumulasi omset & kerugian terhindari, total reduksi emisi CO2e, serta keberlanjutan SDG.\n"
            "- Gunakan MCP tool 'business_overview' untuk membandingkan cabang secara langsung.\n"
            "- DILARANG KERAS menyebutkan bahwa kamu adalah asisten untuk 1 toko/cabang tertentu saja.\n"
            "- Ketika menyajikan data perbandingan cabang, statistik omset, atau daftar metrik, SELALU gunakan format TABEL MARKDOWN (Markdown Table) atau DIAGRAM MERMAID (misal ```mermaid pie atau ```mermaid graph TD) agar data tersaji sangat rapi, terstruktur, dan elegan."
        )


    elif user.role == UserRole.SELLER:
        store_name = user.store.name if user.store else "Toko Anda"
        store_id = str(user.store_id) if user.store_id else "tidak diset"
        prompt += f"\n\nKONTEKS: Kamu membantu SELLER dari toko '{store_name}' (store_id: {store_id}).\n" \
                      "- Kamu HANYA boleh melihat data toko ini, bukan toko lain.\n" \
                      "- Fokus pada: stok, produk hampir expired, omzet harian, review pelanggan.\n" \
                      "- Berikan rekomendasi actionable (misal: 'diskon produk X karena expired 2 hari lagi').\n" \
                      "- Jangan tampilkan data financial sensitif seperti detail wallet toko lain."

    if slots:
        slot_lines = []
        if slots.get("selected_product_id"):
            slot_lines.append(f"- Produk terpilih saat ini: '{slots.get('selected_product_name')}' (ID/UUID: {slots.get('selected_product_id')})")
        if slot_lines:
            prompt += "\n\nKONTEKS VARIABEL SESI OBROLAN AKTIF:\n" + "\n".join(slot_lines)

    if active_skill == "strategi":
        prompt += (
            "\n\nSKILL AKTIF: STRATEGI BISNIS & MARKETING 🧠\n"
            "- Kamu saat ini berada dalam mode Asisten Strategi Bisnis.\n"
            "- Tugas utama kamu adalah mencari dan memberikan strategi bisnis, pemasaran, efisiensi operasional, dan pengurangan limbah pangan (food waste) terbaik.\n"
            "- Jawab dengan saran taktis, langkah-demi-langkah (actionable steps), dan pertimbangan lokal/nasional.\n"
            "- Kamu memiliki akses ke tool 'web_search_and_crawl'. Gunakan tool ini jika memerlukan informasi luar seperti tren pasar terbaru, data kompetitor, regulasi pemerintah terkini, atau referensi industri eksternal.\n"
            "- Jangan ragu melakukan pencarian web terlebih dahulu sebelum merumuskan strategi."
        )
    elif active_skill == "visualisasi":
        prompt += (
            "\n\nSKILL AKTIF: VISUALISASI DATA (CHARTS) 📊\n"
            "- Kamu saat ini berada dalam mode Asisten Visualisasi Data.\n"
            "- Tugas utama kamu adalah menyajikan data dalam bentuk grafik yang indah dan interaktif.\n"
            "- Ketika pengguna meminta grafik, tren, perbandingan, atau ringkasan numerik, kamu WAJIB memanggil database tools yang relevan untuk mengambil data nyata (seperti sales_summary, carbon_summary, business_overview), lalu memformat data tersebut ke dalam blok kode khusus ```chart ... ```.\n"
            "- Format blok chart HARUS berupa string JSON valid yang berisi konfigurasi Chart.js yang bisa langsung di-render oleh frontend. Contoh format:\n"
            "```chart\n"
            "{\n"
            '  "type": "bar",\n'
            '  "data": {\n'
            '    "labels": ["Label A", "Label B"],\n'
            '    "datasets": [\n'
            "      {\n"
            '        "label": "Nama Metrik",\n'
            '        "data": [100, 200],\n'
            '        "borderColor": "#0F3D2E",\n'
            '        "backgroundColor": "rgba(15, 61, 46, 0.2)"\n'
            "      }\n"
            "    ]\n"
            "  },\n"
            '  "options": {\n'
            '    "responsive": true\n'
            "  }\n"
            "}\n"
            "```\n"
            "- Tipe chart yang didukung oleh frontend adalah: 'bar', 'line', dan 'doughnut'.\n"
            "- Selalu jelaskan singkat apa yang ditampilkan grafik tersebut di bawah blok grafik."
        )

    return prompt


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_service = ConversationService(db)
        self.memory_service = MemoryService(db)
        self.tool_call_service = ToolCallService(db)

    async def get_response(self, user_id: uuid.UUID, conversation_id: uuid.UUID, user_message: str) -> str:
        # Load user context with business, stores, and store relationships
        user_res = await self.db.execute(
            select(User)
            .options(
                selectinload(User.business).selectinload(Business.stores),
                selectinload(User.store)
            )
            .where(User.id == user_id)
        )
        user = user_res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        conv = await self.conv_service.get_conversation(conversation_id)
        if not conv or conv.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        await self.conv_service.add_message(conversation_id, "user", user_message)

        is_enterprise_user = (
            user.role in (UserRole.OWNER, UserRole.ADMIN)
            or (user.business_id is not None and not user.store_id)
        )

        # Build allowed store IDs for verification boundaries
        allowed_store_ids = []
        if is_enterprise_user:
            if user.business and user.business.stores:
                allowed_store_ids = [str(s.id) for s in user.business.stores]
        elif user.role == UserRole.SELLER:
            if user.store_id:
                allowed_store_ids = [str(user.store_id)]

        # Dynamically build system prompt
        from app.modules.chat.service.session_service import SessionService
        slots = await SessionService.get_slots(conversation_id)
        system_prompt = build_system_prompt(user, slots, active_skill=conv.active_skill)

        llm = AIFactory.get_llm_provider()

        # 1. Intent Detection Layer
        intent_system = (
            "Klasifikasikan pesan terbaru dari pengguna ke dalam salah satu dari intent berikut:\n"
            "- SEARCH_PRODUCT: Pengguna ingin mencari/mengecek/menjelajahi produk surplus yang tersedia.\n"
            "- CHECK_STOCK: Pengguna ingin mengecek ketersediaan stok, kuantitas batch, atau masa kedaluwarsa (expiry) produk.\n"
            "- CHECK_ORDER: Pengguna ingin melihat riwayat transaksi, performa penjualan harian/bulanan, omzet, detail wallet toko.\n"
            "- ANALYTICS_RECOMMENDATIONS: Pengguna meminta rekomendasi stok, wawasan bisnis, tren penjualan terendah/tertinggi, atau ramalan penjualan produk untuk hari tertentu.\n"
            "- GENERAL_CHAT: Sapaan (halo/hai), terima kasih, obrolan umum, penjelasan konsep, atau topik di luar data dinamis toko.\n\n"
            "HANYA balas dengan nama intent dalam huruf kapital (contoh: GENERAL_CHAT). Jangan sertakan karakter, spasi tambahan, atau teks penjelasan lainnya."
        )

        intent_str = "GENERAL_CHAT"
        try:
            intent_response = await llm.generate_response(user_message, system_prompt=intent_system)
            cleaned_intent = intent_response.strip().upper()
            for candidate in ["SEARCH_PRODUCT", "CHECK_STOCK", "CHECK_ORDER", "ANALYTICS_RECOMMENDATIONS", "GENERAL_CHAT"]:
                if candidate in cleaned_intent:
                    intent_str = candidate
                    break
        except Exception:
            intent_str = "GENERAL_CHAT"

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Classified user intent: {intent_str}")

        # 2. Filter schemas based on intent & role
        effective_role = UserRole.OWNER if is_enterprise_user else user.role
        allowed_tools = mcp_registry.get_tool_schemas_for_role(effective_role)


        if intent_str == "GENERAL_CHAT" and conv.active_skill != "strategi":
            tool_schemas = []
        else:
            # Expose the full suite of allowed tools for their role to enable entity resolution
            # and complex multi-step reasoning.
            tool_schemas = allowed_tools



        # Build context-safe messages using sliding window (last 10 messages)
        messages = [{"role": "system", "content": system_prompt}]
        history_pool = list(conv.messages)
        # Keep last 10 messages
        recent_history = history_pool[-10:] if len(history_pool) > 10 else history_pool

        for msg in recent_history:
            content = msg.content or ""
            # Truncate oversized historical messages/tool outputs in older turns
            if len(content) > 2000 and msg.role in ("tool", "assistant"):
                content = content[:1500] + "\n... [Data historis dipotong untuk efisiensi konteks]"
            messages.append({"role": msg.role, "content": content})

        for turn in range(MAX_TOOL_TURNS):
            kwargs = {}
            if tool_schemas:
                kwargs["tools"] = tool_schemas

            try:
                response = await llm.generate_chat_response(messages, **kwargs)
            except Exception as err:
                err_str = str(err).lower()
                if any(kw in err_str for kw in ["context", "token", "length", "1048565", "invalid_request_error"]):
                    logger.warning("Context window exceeded (%s). Pruning history to minimal user prompt and retrying...", err)
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ]
                    response = await llm.generate_chat_response(messages, **kwargs)
                else:
                    raise

            if not response.tool_calls:
                final_content = response.content or ""
                await self.conv_service.add_message(conversation_id, "assistant", final_content)
                await self._auto_summarize_title(conversation_id, conv)
                return final_content

            assistant_msg_obj = await self.conv_service.add_message(
                conversation_id, "assistant", response.content or ""
            )

            openai_tool_calls = []
            for tc in response.tool_calls:
                openai_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, default=json_serial)
                    }
                })

            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": openai_tool_calls
            })

            for tc in response.tool_calls:
                result = await self.tool_call_service.execute_and_log_tool(
                    chat_message_id=assistant_msg_obj.id,
                    role=user.role,
                    allowed_store_ids=allowed_store_ids,
                    tool_name=tc.name,
                    arguments=tc.arguments
                )
                
                # Update session slots on successful product search
                if tc.name == "product_search" and isinstance(result, dict) and result.get("success") is True:
                    data = result.get("data", {})
                    products = data.get("results", [])
                    if len(products) == 1:
                        await SessionService.set_slots(
                            conversation_id,
                            {
                                "selected_product_id": str(products[0]["id"]),
                                "selected_product_name": products[0]["name"]
                            }
                        )
                    elif len(products) > 1:
                        await SessionService.set_slots(
                            conversation_id,
                            {
                                "selected_product_id": None,
                                "selected_product_name": None
                            }
                        )
                
                # Truncate large tool result payloads if they exceed 5KB before putting into LLM messages
                tool_res_str = json.dumps(result, default=json_serial)
                if len(tool_res_str) > 5000:
                    tool_res_str = tool_res_str[:4000] + '... "info": "Hasil data dipotong untuk efisiensi"}'

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_res_str
                })

        fallback = "Maaf, saya tidak bisa menyelesaikan permintaan Anda dalam beberapa langkah. Silakan coba lagi."
        await self.conv_service.add_message(conversation_id, "assistant", fallback)
        await self._auto_summarize_title(conversation_id, conv)
        return fallback

    async def _auto_summarize_title(self, conversation_id: uuid.UUID, conv) -> None:
        try:
            from app.modules.chat.service.summary_service import ChatSummaryService
            # Only summarize if it's a default title or first exchange
            if conv.title and not (conv.title.startswith("Chat ") or conv.title.startswith("Obrolan ") or conv.title == "New Conversation" or "Percakapan" in conv.title):
                # If title is already custom, don't overwrite
                return
            
            # Fetch latest messages directly from DB (including newly flushed ones in transaction)
            from sqlalchemy import select
            from app.modules.chat.models import ChatMessage
            
            result = await self.db.execute(
                select(ChatMessage)
                .filter(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.created_at.asc())
            )
            db_messages = result.scalars().all()
            
            # Format message list for summarize_conversation helper
            formatted = [{"role": m.role, "content": m.content} for m in db_messages if m.role in ["user", "assistant"]]
            
            summary_service = ChatSummaryService(self.db)
            summary = await summary_service.summarize_conversation(conversation_id, formatted)
            
            # Clean up the summary title (keep it short: max 40 chars, remove quotes, etc.)
            clean_title = summary.strip().strip('"').strip("'")
            if len(clean_title) > 40:
                clean_title = clean_title[:37] + "..."
                
            conv.title = clean_title
            self.db.add(conv)
            await self.db.flush()
        except Exception as e:
            # Don't fail the chat response if summarizing fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Auto-summarizing title failed: {e}")
