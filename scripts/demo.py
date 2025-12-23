#!/usr/bin/env python3
# =============================================================================
# OSINT OA - Demo Script
# =============================================================================
"""
Demo script for testing OSINT agents.

Usage:
    python scripts/demo.py [agent_name] [query]
    
Examples:
    python scripts/demo.py                              # Interactive mode
    python scripts/demo.py TavilySearchAgent "APT29"    # Specific agent
    python scripts/demo.py --list                       # List agents
"""

import argparse
import asyncio
import logging
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_agents():
    """List all available agents."""
    from agents.registry import AgentRegistry
    
    print("\n📋 Available OSINT Agents:")
    print("=" * 60)
    
    agents = AgentRegistry.list_available()
    
    for agent in agents:
        status = "✅" if agent["available"] else "❌"
        name = agent["name"]
        desc = agent["description"][:50] + "..." if len(agent["description"]) > 50 else agent["description"]
        
        print(f"{status} {name:25s} - {desc}")
        
        if not agent["available"]:
            print(f"   └── {agent['reason']}")
    
    print("=" * 60)
    print(f"\nTotal: {len(agents)} agents")


def run_agent(agent_name: str, query: str):
    """Run a specific agent with a query."""
    from agents.registry import AgentRegistry
    
    print(f"\n🔍 Running {agent_name}...")
    print(f"📝 Query: {query}")
    print("=" * 60)
    
    agent = AgentRegistry.get(agent_name)
    
    if not agent:
        print(f"❌ Agent '{agent_name}' not found")
        print("\nAvailable agents:")
        for name in AgentRegistry.list_all():
            print(f"  - {name}")
        return
    
    available, reason = agent.is_available()
    if not available:
        print(f"❌ Agent not available: {reason}")
        return
    
    try:
        result = agent.run(query)
        print("\n📊 Result:")
        print("-" * 60)
        print(result)
        print("-" * 60)
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Agent execution failed")


def run_investigation(query: str):
    """Run a full investigation using ControlAgent."""
    from agents.control import ControlAgent
    
    print(f"\n🔍 Starting investigation...")
    print(f"📝 Topic: {query}")
    print("=" * 60)
    
    agent = ControlAgent()
    
    try:
        result = agent.investigate(query, depth="standard")
        
        print("\n📊 Investigation Result:")
        print("-" * 60)
        
        if result.get("success"):
            print(result.get("report", "No report generated"))
        else:
            print(f"❌ Investigation failed: {result.get('error')}")
        
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Investigation failed")


def interactive_mode():
    """Run in interactive mode."""
    print("\n🤖 OSINT Demo - Interactive Mode")
    print("=" * 60)
    print("Commands:")
    print("  list              - List available agents")
    print("  <agent> <query>   - Run specific agent")
    print("  investigate <q>   - Full investigation")
    print("  quit              - Exit")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Bye!")
                break
            
            if user_input.lower() == "list":
                list_agents()
                continue
            
            parts = user_input.split(maxsplit=1)
            
            if parts[0].lower() == "investigate" and len(parts) > 1:
                run_investigation(parts[1])
            elif len(parts) >= 2:
                run_agent(parts[0], parts[1])
            else:
                print("Usage: <agent_name> <query>")
                print("       investigate <query>")
                print("       list")
                
        except KeyboardInterrupt:
            print("\n👋 Bye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="OSINT Demo Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                              List all agents
  %(prog)s TavilySearchAgent "APT29"           Run specific agent
  %(prog)s --investigate "ransomware 2025"     Full investigation
  %(prog)s                                     Interactive mode
        """
    )
    
    parser.add_argument("agent", nargs="?", help="Agent name to run")
    parser.add_argument("query", nargs="?", help="Query to execute")
    parser.add_argument("--list", "-l", action="store_true", help="List available agents")
    parser.add_argument("--investigate", "-i", metavar="QUERY", help="Run full investigation")
    
    args = parser.parse_args()
    
    if args.list:
        list_agents()
    elif args.investigate:
        run_investigation(args.investigate)
    elif args.agent and args.query:
        run_agent(args.agent, args.query)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
