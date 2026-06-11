resurva_backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── routes/
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── stores.py
│   │           ├── products.py
│   │           ├── inventory.py
│   │           ├── orders.py
│   │           ├── discounts.py
│   │           ├── wallets.py
│   │           ├── reports.py
│   │           └── chat.py
│   │
│   ├── modules/
│   │   │
│   │   ├── auth/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── constants.py
│   │   │   └── service/
│   │   │       ├── **init**.py
│   │   │       ├── auth_service.py
│   │   │       ├── jwt_service.py
│   │   │       └── access_context_service.py
│   │   │
│   │   ├── business/
│   │   ├── users/
│   │   ├── stores/
│   │   ├── products/
│   │   ├── inventory/
│   │   ├── reviews/
│   │   ├── discounts/
│   │   ├── orders/
│   │   ├── transactions/
│   │   ├── wallets/
│   │   ├── summaries/
│   │   ├── carbon/
│   │   │
│   │   └── chat/
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── repository.py
│   │       ├── constants.py
│   │       └── service/
│   │           ├── **init**.py
│   │           ├── chat_service.py
│   │           ├── conversation_service.py
│   │           ├── memory_service.py
│   │           ├── tool_call_service.py
│   │           └── summary_service.py
│   │
│   ├── ai/
│   │   ├── interfaces/
│   │   │   └── llm_provider.py
│   │   │
│   │   ├── providers/
│   │   │   ├── deepseek.py
│   │   │   ├── openai.py
│   │   │   └── anthropic.py
│   │   │
│   │   ├── factory.py
│   │   └── exceptions.py
│   │
│   ├── mcp/
│   │   ├── base_tool.py
│   │   ├── registry.py
│   │   │
│   │   ├── tools/
│   │   │   ├── product_search_tool.py
│   │   │   ├── inventory_tool.py
│   │   │   ├── sales_summary_tool.py
│   │   │   ├── carbon_summary_tool.py
│   │   │   ├── expiry_alert_tool.py
│   │   │   └── wallet_tool.py
│   │   │
│   │   └── orchestrator.py
│   │
│   ├── storage/
│   │   ├── interfaces/
│   │   │   └── storage_provider.py
│   │   │
│   │   ├── providers/
│   │   │   ├── local_storage.py
│   │   │   ├── s3_storage.py
│   │   │   └── minio_storage.py
│   │   │
│   │   ├── factory.py
│   │   └── utils.py
│   │
│   ├── prompts/
│   │   ├── system/
│   │   ├── chat/
│   │   └── tools/
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── seeders/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   ├── pagination.py
│   │   └── logging.py
│   │
│   └── utils/
│       ├── datetime.py
│       ├── files.py
│       └── validators.py
│
├── migrations/
│
├── tests/
│
├── uploads/
│   ├── stores/
│   ├── products/
│   ├── reviews/
│   └── chat/
│
├── .env
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
