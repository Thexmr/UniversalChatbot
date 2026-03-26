"""
Adapters Package - Plattform-spezifische Adapter für UniversalChatbot.
"""

from .whatsapp_adapter import WhatsAppAdapter, WhatsAppMessage

__all__ = ["WhatsAppAdapter", "WhatsAppMessage"]