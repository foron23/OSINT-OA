# =============================================================================
# Consolidator Agent - Report Publishing
# =============================================================================
"""
Consolidator agent for publishing reports to Telegram.

Provides:
- ConsolidatorAgent: Publishes investigation reports to Telegram channels
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.telegram import TelegramMCPPublishReportTool

logger = logging.getLogger(__name__)


class ConsolidatorAgent(LangChainAgent):
    """
    Consolidator agent for publishing reports to Telegram.
    
    Takes investigation reports and publishes them to 
    configured Telegram channels/dialogs.
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="ConsolidatorAgent",
            description="Publishes OSINT reports to Telegram channels",
            tools=["telegram_publish_report"],
            supported_queries=["publish", "send", "telegram", "distribute"],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get Telegram publishing tools."""
        return [TelegramMCPPublishReportTool()]
    
    def _get_system_prompt(self) -> str:
        return """You are the Consolidator Agent - responsible for publishing OSINT reports.

Your role is to:
1. RECEIVE investigation reports
2. FORMAT them appropriately for Telegram
3. PUBLISH to the configured channel

Telegram formatting guidelines:
- Use clear headers with emoji indicators
- Keep messages concise but informative
- Use bullet points for lists
- Highlight critical information
- Include source attribution

Report sections:
📋 **Report Title**
📅 Date and time
📝 Key findings
⚠️ Risk assessment (if applicable)
🔗 Sources
📌 Recommendations

Message length:
- Telegram has a 4096 character limit per message
- If report is longer, summarize key points
- Focus on actionable intelligence

When publishing:
1. Use telegram_publish_report tool
2. Confirm successful delivery
3. Report any errors

Publish professional, well-formatted reports."""
    
    def publish_report(
        self,
        report: str,
        title: Optional[str] = None,
        dialog_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a report to Telegram.
        
        Args:
            report: The report content to publish
            title: Optional title for the report
            dialog_name: Specific dialog to publish to
            
        Returns:
            Publication result
        """
        if title:
            query = f"Publish this report titled '{title}':\n\n{report}"
        else:
            query = f"Publish this report:\n\n{report}"
        
        if dialog_name:
            query += f"\n\nPublish to: {dialog_name}"
        
        try:
            result = self.run(query)
            return {
                "success": True,
                "message": "Report published successfully",
                "details": result,
            }
        except Exception as e:
            logger.error(f"Failed to publish report: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def send_alert(
        self,
        title: str,
        content: str,
        severity: str = "INFO"
    ) -> Dict[str, Any]:
        """
        Send an alert to Telegram.
        
        Args:
            title: Alert title
            content: Alert content
            severity: Alert severity (INFO, WARNING, CRITICAL)
            
        Returns:
            Send result
        """
        severity_emoji = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "CRITICAL": "🚨",
        }
        emoji = severity_emoji.get(severity.upper(), "📢")
        
        alert = f"{emoji} **{title}**\n\n{content}"
        
        return self.publish_report(alert, title=f"Alert: {title}")
