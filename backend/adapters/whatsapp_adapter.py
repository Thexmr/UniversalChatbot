"""
WhatsApp Adapter für UniversalChatbot.
Plattform-spezifische Nachrichtenformatierung.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WhatsAppMessage:
    """Repräsentiert eine WhatsApp-Nachricht."""
    sender: str
    content: str
    is_group: bool = False
    group_name: Optional[str] = None
    timestamp: Optional[str] = None
    message_type: str = "text"  # text, media, voice, etc.
    
    def format_for_llm(self) -> str:
        """Formatiert die Nachricht für den LLM-Kontext."""
        prefix = ""
        if self.is_group and self.group_name:
            prefix = f"[{self.group_name}] "
        return f"{prefix}{self.sender}: {self.content}"


class WhatsAppAdapter:
    """
    Adapter für WhatsApp-spezifische Formatierung.
    
    Konvertiert Daten aus der Browser-Erweiterung in
    einheitliche Formate für den Chat-Manager.
    """
    
    # Muster für WhatsApp Web DOM-Elemente (könnte von Extension kommen)
    MESSAGE_SELECTORS = {
        "message": ".message-in, .message-out",
        "content": ".selectable-text span",
        "sender": "[data-pre-plain-text]",
        "timestamp": ".copyable-text[data-pre-plain-text]"
    }
    
    def __init__(self):
        self.current_chat: Optional[str] = None
        self.user_name: Optional[str] = None
    
    def parse_incoming_message(self, data: Dict[str, Any]) -> WhatsAppMessage:
        """
        Parst eine eingehende Nachricht von der Extension.
        
        Args:
            data: Rohdaten von der Extension
        
        Returns:
            WhatsAppMessage Objekt
        """
        return WhatsAppMessage(
            sender=data.get("sender", "Unbekannt"),
            content=data.get("content", ""),
            is_group=data.get("is_group", False),
            group_name=data.get("group_name"),
            timestamp=data.get("timestamp"),
            message_type=data.get("type", "text")
        )
    
    def format_outgoing_message(
        self, 
        text: str, 
        auto_send: bool = False
    ) -> Dict[str, Any]:
        """
        Formatiert eine ausgehende Nachricht für WhatsApp.
        
        Args:
            text: Antworttext
            auto_send: Ob automatisch gesendet werden soll
        
        Returns:
            Formatierte Nachricht
        """
        # WhatsApp-spezifische Formatierungen
        formatted_text = self._apply_whatsapp_formatting(text)
        
        result = {
            "type": "whatsapp_response",
            "text": formatted_text,
            "auto_send": auto_send,
            "formatting": {
                "bold": bool(re.search(r'\*(.+?)\*', text)),
                "italic": bool(re.search(r'_(.+?)_', text)),
                "code": bool(re.search(r'`(.+?)`', text))
            }
        }
        
        return result
    
    def _apply_whatsapp_formatting(self, text: str) -> str:
        """
        Wendet WhatsApp-Formatierung auf den Text an.
        
        Args:
            text: Rohtext
        
        Returns:
            Formatierter Text
        """
        # Unicode-Emoji Unterstützung
        text = self._convert_emoji_shortcodes(text)
        return text
    
    def _convert_emoji_shortcodes(self, text: str) -> str:
        """
        Konvertiert Emoji-Shortcodes zu Unicode.
        
        Args:
            text: Text mit Shortcodes
        
        Returns:
            Text mit Unicode-Emojis
        """
        emoji_map = {
            ":)": "🙂",
            ":(": "🙁",
            ":D": "😀",
            ":P": "😛",
            "<3": "❤️",
            ":thumbsup:": "👍",
            ":thumbsdown:": "👎",
            ":wave:": "👋",
            ":ok:": "👌",
            ":fire:": "🔥",
            ":star:": "⭐",
            ":check:": "✅",
            ":cross:": "❌",
        }
        
        result = text
        for shortcode, emoji in emoji_map.items():
            result = result.replace(shortcode, emoji)
        
        return result
    
    def extract_chat_context(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extrahiert Chat-Kontext aus WhatsApp-Nachrichten.
        
        Args:
            messages: Liste von Nachrichten
        
        Returns:
            Formatierte Nachrichten für LLM
        """
        context = []
        for msg in messages:
            parsed = self.parse_incoming_message(msg)
            context.append({
                "role": "user" if msg.get("is_incoming", True) else "assistant",
                "content": parsed.format_for_llm()
            })
        return context
    
    def sanitize_for_whatsapp(self, text: str) -> str:
        """
        Bereinigt Text für WhatsApp (länge, Zeichen, etc.).
        
        Args:
            text: Rohtext
        
        Returns:
            Bereinigter Text
        """
        # Maximale Länge (WhatsApp erlaubt sehr lange Nachrichten, aber wir begrenzen)
        max_length = 4000
        
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."
        
        # Entferne potenziell problematische Zeichen
        # Erlaube aber Unicode und Emoji
        return text
    
    def detect_message_type(self, content: str) -> str:
        """
        Erkennt den Nachrichtentyp anhand des Inhalts.
        
        Args:
            content: Nachrichteninhalt
        
        Returns:
            Typ: text, url, number, question, etc.
        """
        if re.match(r'https?://', content):
            return "url"
        if re.match(r'^[\d\s\-\(\)\.]+$', content):
            return "number"
        if re.match(r'.*\?$', content):
            return "question"
        return "text"


def create_session_from_whatsapp(
    chat_id: str,
    chat_name: str,
    is_group: bool
) -> Dict[str, Any]:
    """
    Erstellt eine Session aus WhatsApp-Chat-Informationen.
    
    Args:
        chat_id: Eindeutige Chat-ID
        chat_name: Anzeigename des Chats
        is_group: Ob es sich um eine Gruppe handelt
    
    Returns:
        Session-Metadaten
    """
    return {
        "platform": "whatsapp",
        "platform_chat_id": chat_id,
        "platform_chat_name": chat_name,
        "is_group": is_group,
        "adapter": "whatsapp"
    }