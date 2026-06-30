import asyncio
import uuid
import sys
import os

# Set PYTHONPATH to current directory so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load all models to initialize ORM mappers
import tests.test_chatbot_security
from app.db.session import SessionLocal
from app.modules.chat.service.chat_service import ChatService
from app.modules.chat.service.conversation_service import ConversationService
from app.modules.chat.schemas import ConversationCreate

SELLER_USER_ID = uuid.UUID("15ff188d-04bf-42f3-b32f-05eb81a2cf85")
STORE_ID = uuid.UUID("6dab7646-995d-4057-bcb6-2138e7a33fec")

QUESTIONS = [
    "Berapa sisa stok untuk produk Muffin Blueberry saat ini? Apakah ada batch yang hampir kedaluwarsa?",
    "Tolong berikan rekomendasi stok produksi untuk Roti Abon Sapi besok hari Sabtu. Berapa sisa stoknya hari ini?",
    "Lakukan analisis performa produk Donat Kentang Gula. Berapa ratingnya dan apakah produk ini perlu dikaji ulang untuk dihentikan produksinya?",
    "Berapa total omzet penjualan toko saya di Tebet selama sebulan terakhir? Berapa banyak pesanan yang selesai?",
    "Tampilkan daftar seluruh produk di toko saya beserta status kesehatannya dari yang paling buruk skornya. Produk apa saja yang statusnya RETIRE?"
]

async def main():
    print("Starting difficult questions test...")
    async with SessionLocal() as db:
        conv_service = ConversationService(db)
        chat_service = ChatService(db)
        
        # Create a new conversation for testing
        schema = ConversationCreate(store_id=STORE_ID, title="Pengujian Pertanyaan Sulit")
        conv = await conv_service.create_conversation(
            user_id=SELLER_USER_ID,
            schema=schema
        )
        conv_id = conv.id
        print(f"Created conversation ID: {conv_id}")
        
        output_lines = []
        output_lines.append("=" * 60)
        output_lines.append("PENGUJIAN PERTANYAAN SULIT - CHATBOT SELLER & OWNER")
        output_lines.append(f"Conversation ID: {conv_id}")
        output_lines.append(f"Store ID: {STORE_ID}")
        output_lines.append("=" * 60 + "\n")
        
        for idx, q in enumerate(QUESTIONS, 1):
            print(f"\nProcessing Question {idx}/{len(QUESTIONS)}: {q}")
            output_lines.append(f"--- PERTANYAAN {idx} ---")
            output_lines.append(f"Q: {q}")
            
            response = None
            for attempt in range(1, 4):
                try:
                    # Call chat_service
                    response = await chat_service.get_response(
                        user_id=SELLER_USER_ID,
                        conversation_id=conv_id,
                        user_message=q
                    )
                    break
                except Exception as e:
                    print(f"Attempt {attempt} failed: {e}")
                    if attempt == 3:
                        import traceback
                        response = f"[Gagal mendapatkan jawaban setelah 3 percobaan] {e}"
                    else:
                        await asyncio.sleep(2)
                
            output_lines.append(f"\nA: {response}")
            output_lines.append("-" * 60 + "\n")
            
        # Write to txt file
        output_path = "/home/mashupsoat/Project/resurva/pertanyaan_project.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\nDone! Output written to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
