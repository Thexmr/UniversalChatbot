# UniversalChatbot Backend Tests

## Run Tests

```bash
cd backend/

# Run all tests
python tests/test_all.py

# Or with pytest
pytest tests/ -v

# Run specific test file
python -m unittest tests.test_chat_manager
```

## Test Structure

- `test_chat_manager.py` - Session and message management tests
- `test_native_host.py` - Native messaging communication tests
- `test_llm_client.py` - LLM API integration tests
- `test_integration.py` - End-to-end flow tests

## Coverage

Tests cover:
- ✅ Session management
- ✅ Message history (max 10)
- ✅ Message routing
- ✅ Error handling
- ✅ LLM client configuration
- ✅ Full integration flow
