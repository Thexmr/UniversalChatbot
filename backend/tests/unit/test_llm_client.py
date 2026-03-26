"""
Unit tests for LLM Client
OpenAI API integration for chat response generation
"""
import unittest
import os
from unittest.mock import Mock, patch, MagicMock

from chatbot.llm_client import LLMClient


class TestLLMClient(unittest.TestCase):
    """Test cases for LLMClient class"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key-12345'})
    @patch('chatbot.llm_client.OpenAI')
    def test_initialization_with_api_key(self, mock_openai_class):
        """Test LLMClient initializes with API key"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        
        self.assertEqual(client.api_key, 'test-key-12345')
        self.assertTrue(client.is_configured())
        mock_openai_class.assert_called_once_with(api_key='test-key-12345')
    
    @patch.dict('os.environ', {}, clear=True)
    def test_initialization_without_api_key(self):
        """Test LLMClient handles missing API key"""
        client = LLMClient()
        
        self.assertIsNone(client.api_key)
        self.assertIsNone(client.client)
        self.assertFalse(client.is_configured())
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_initialization_with_mock_openai(self, mock_openai_class):
        """Test initialization with mock OpenAI"""
        mock_openai_class.return_value = MagicMock()
        
        client = LLMClient()
        
        self.assertTrue(client.is_configured())
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'LLM_MODEL': 'gpt-4'})
    @patch('chatbot.llm_client.OpenAI')
    def test_custom_model_from_env(self, mock_openai_class):
        """Test custom model from environment variable"""
        mock_openai_class.return_value = MagicMock()
        
        client = LLMClient()
        
        self.assertEqual(client.model, 'gpt-4')
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_default_model(self, mock_openai_class):
        """Test default model when env var not set"""
        mock_openai_class.return_value = MagicMock()
        
        client = LLMClient()
        
        self.assertEqual(client.model, 'gpt-3.5-turbo')
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_success(self, mock_openai_class):
        """Test successful response generation"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, this is a test response!"
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = [{"role": "user", "content": "Hello"}]
        
        response = client.generate_response(context)
        
        self.assertEqual(response, "Hello, this is a test response!")
        
        # Verify API was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args[1]['model'], 'gpt-3.5-turbo')
        self.assertEqual(call_args[1]['max_tokens'], 500)
        self.assertEqual(call_args[1]['temperature'], 0.7)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_with_system_prompt(self, mock_openai_class):
        """Test response generation with custom system prompt"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Custom response"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = [{"role": "user", "content": "Hello"}]
        custom_prompt = "You are a helpful coding assistant"
        
        response = client.generate_response(context, system_prompt=custom_prompt)
        
        # Verify system message was included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], custom_prompt)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_with_context(self, mock_openai_class):
        """Test response generation with conversation context"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response based on context"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        response = client.generate_response(context)
        
        # Verify all context messages were included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        self.assertEqual(len(messages), 4)  # system + 3 context messages
        self.assertEqual(messages[1]["content"], "Hello")
        self.assertEqual(messages[2]["content"], "Hi there!")
        self.assertEqual(messages[3]["content"], "How are you?")
    
    @patch.dict('os.environ', {}, clear=True)
    def test_generate_response_not_configured(self):
        """Test response when LLM is not configured"""
        client = LLMClient()
        context = [{"role": "user", "content": "Hello"}]
        
        response = client.generate_response(context)
        
        self.assertEqual(response, "[LLM not configured - check OPENAI_API_KEY]")
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_api_error(self, mock_openai_class):
        """Test handling of API errors"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = [{"role": "user", "content": "Hello"}]
        
        response = client.generate_response(context)
        
        self.assertEqual(response, "[Error generating response - check logs]")
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_empty_context(self, mock_openai_class):
        """Test response generation with empty context"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "General greeting"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = []
        
        response = client.generate_response(context)
        
        # Should still work with just system message
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        self.assertEqual(len(messages), 1)  # Only system message
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI')
    def test_generate_response_strips_whitespace(self, mock_openai_class):
        """Test that response has whitespace stripped"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Trimmed response  \n\n"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        client = LLMClient()
        context = [{"role": "user", "content": "Hello"}]
        
        response = client.generate_response(context)
        
        self.assertEqual(response, "Trimmed response")
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('chatbot.llm_client.OpenAI', None)
    def test_initialization_without_openai_package(self):
        """Test initialization when openai package is not available"""
        client = LLMClient()
        
        self.assertIsNone(client.client)
        self.assertFalse(client.is_configured())
    
    def test_default_system_prompt(self):
        """Test that default system prompt exists"""
        self.assertIsNotNone(LLMClient.DEFAULT_SYSTEM_PROMPT)
        self.assertIn("helpful", LLMClient.DEFAULT_SYSTEM_PROMPT.lower())


if __name__ == '__main__':
    unittest.main()
