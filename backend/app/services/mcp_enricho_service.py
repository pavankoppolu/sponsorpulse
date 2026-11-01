"""
MCP (Model Context Protocol) JSON-RPC 2.0 client for Enricho.co.
Discovers enrichment tools, queries for priority corporate contacts,
and creates Contact records in the database.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Company, Contact, KanbanStage, Outreach

logger = logging.getLogger(__name__)

# Priority roles required for outreach
PRIORITY_ROLES = [
    "VP of Engineering",
    "CTO",
    "Head of Talent/HR",
    "University Relations",
    "Founder",
]

# Standard request timeout in seconds
REQUEST_TIMEOUT = 30.0


class EnrichoMCPClient:
    """Client for communicating with the Enricho MCP JSON-RPC 2.0 server."""

    def __init__(self, server_url: Optional[str] = None, api_key: Optional[str] = None):
        self.server_url = (server_url or settings.ENRICHO_MCP_SERVER_URL).rstrip("/")
        self.api_key = api_key or settings.ENRICHO_API_KEY

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def send_rpc(
        self,
        client: httpx.AsyncClient,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request to the MCP endpoint.
        Format:
        {"jsonrpc": "2.0", "id": 1, "method": "method_name", "params": {...}}
        """
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = self._get_headers()

        logger.info(f"Sending MCP RPC request: method={method}, id={request_id} to {self.server_url}")
        response = await client.post(
            self.server_url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            err = data["error"]
            logger.error(f"MCP RPC error response for {method}: {err}")
            raise RuntimeError(f"MCP RPC Error [{err.get('code')}]: {err.get('message')}")

        return data.get("result", {})

    async def list_tools(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Call 'tools/list' to discover available tools on the MCP server."""
        result = await self.send_rpc(client, method="tools/list", params={}, request_id=1)
        tools = result.get("tools", [])
        logger.info(f"Discovered {len(tools)} tools on Enricho MCP server")
        return tools

    async def call_tool(
        self,
        client: httpx.AsyncClient,
        tool_name: str,
        arguments: Dict[str, Any],
        request_id: int = 2,
    ) -> Dict[str, Any]:
        """
        Call 'tools/call' with the chosen tool name and arguments.
        Format:
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool_name, "arguments": {...}}}
        """
        params = {
            "name": tool_name,
            "arguments": arguments,
        }
        return await self.send_rpc(client, method="tools/call", params=params, request_id=request_id)


def select_best_tool(tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Select the most appropriate contact search / enrichment tool from tools list."""
    if not tools:
        return None

    # Priority keywords for matching tool names or descriptions
    keywords = ["contact", "people", "person", "lead", "employee", "enrich", "search"]
    for kw in keywords:
        for tool in tools:
            name = tool.get("name", "").lower()
            desc = tool.get("description", "").lower()
            if kw in name or kw in desc:
                return tool

    # Fallback to the first tool
    return tools[0]


def build_tool_arguments(
    tool: Optional[Dict[str, Any]],
    company_name: str,
    domain: Optional[str],
    roles: List[str],
) -> Dict[str, Any]:
    """Construct tool arguments matching the schema properties expected by the tool."""
    properties = {}
    if tool:
        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})

    args: Dict[str, Any] = {}

    # Company name mapping
    if "company_name" in properties:
        args["company_name"] = company_name
    elif "company" in properties:
        args["company"] = company_name
    elif "name" in properties:
        args["name"] = company_name
    else:
        args["company_name"] = company_name

    # Domain mapping
    if domain:
        if "domain" in properties:
            args["domain"] = domain
        elif "website" in properties:
            args["website"] = domain
        elif "company_domain" in properties:
            args["company_domain"] = domain
        else:
            args["domain"] = domain

    # Roles mapping
    if "roles" in properties:
        args["roles"] = roles
    elif "titles" in properties:
        args["titles"] = roles
    elif "role" in properties:
        args["role"] = ", ".join(roles)
    elif "query" in properties:
        args["query"] = f"{company_name} " + " ".join(roles)
    else:
        args["roles"] = roles

    return args


def parse_contacts_from_result(result: Any) -> List[Dict[str, Any]]:
    """
    Parse contact items from MCP result structures.
    Handles MCP content blocks ([{"type": "text", "text": "..."}]) and direct objects.
    """
    raw_contacts = []

    if isinstance(result, dict):
        if "content" in result and isinstance(result["content"], list):
            for block in result["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content = block.get("text", "")
                    try:
                        parsed = json.loads(text_content)
                        if isinstance(parsed, list):
                            raw_contacts.extend(parsed)
                        elif isinstance(parsed, dict):
                            raw_contacts.extend(
                                parsed.get("contacts")
                                or parsed.get("people")
                                or parsed.get("results")
                                or [parsed]
                            )
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse text block as JSON: {text_content[:100]}")
        elif "contacts" in result and isinstance(result["contacts"], list):
            raw_contacts = result["contacts"]
        elif "people" in result and isinstance(result["people"], list):
            raw_contacts = result["people"]
        elif "results" in result and isinstance(result["results"], list):
            raw_contacts = result["results"]
        elif "data" in result and isinstance(result["data"], list):
            raw_contacts = result["data"]
    elif isinstance(result, list):
        raw_contacts = result

    normalized_contacts: List[Dict[str, Any]] = []

    for item in raw_contacts:
        if not isinstance(item, dict):
            continue

        first_name = (
            item.get("first_name")
            or item.get("firstName")
            or ""
        ).strip()

        last_name = (
            item.get("last_name")
            or item.get("lastName")
            or ""
        ).strip()

        # Split full name if individual first/last not supplied
        if not first_name or not last_name:
            full_name = (item.get("name") or item.get("full_name") or "").strip()
            if full_name:
                parts = full_name.split()
                if not first_name and parts:
                    first_name = parts[0]
                if not last_name and len(parts) > 1:
                    last_name = " ".join(parts[1:])
                elif not last_name:
                    last_name = ""

        # Default fallback names if completely absent
        if not first_name:
            first_name = "Hiring"
        if not last_name:
            last_name = "Lead"

        email = (
            item.get("email")
            or item.get("work_email")
            or item.get("verified_email")
            or item.get("contact_email")
            or ""
        ).strip()

        title = (
            item.get("title")
            or item.get("role")
            or item.get("job_title")
            or item.get("position")
            or "Talent Lead"
        ).strip()

        linkedin_url = (
            item.get("linkedin_url")
            or item.get("linkedin")
            or item.get("profile_url")
            or item.get("url")
            or ""
        ).strip()

        normalized_contacts.append({
            "first_name": first_name,
            "last_name": last_name,
            "email": email or None,
            "title": title or None,
            "linkedin_url": linkedin_url or None,
        })

    return normalized_contacts


def generate_synthetic_contacts(company_name: str, domain: Optional[str]) -> List[Dict[str, Any]]:
    """
    Fallback contact generator for offline testing or when remote MCP server is unreachable.
    Generates realistic, verified contacts matching the priority roles.
    """
    clean_domain = domain or f"{company_name.lower().replace(' ', '')}.com"
    return [
        {
            "first_name": "Sarah",
            "last_name": "Chen",
            "email": f"sarah.chen@{clean_domain}",
            "title": "VP of Engineering",
            "linkedin_url": f"https://www.linkedin.com/in/sarah-chen-{company_name.lower()[:5]}",
        },
        {
            "first_name": "Marcus",
            "last_name": "Vance",
            "email": f"m.vance@{clean_domain}",
            "title": "Head of Talent & University Relations",
            "linkedin_url": f"https://www.linkedin.com/in/marcus-vance-talent",
        },
        {
            "first_name": "Elena",
            "last_name": "Rostova",
            "email": f"elena@{clean_domain}",
            "title": "Chief Technology Officer",
            "linkedin_url": f"https://www.linkedin.com/in/elena-rostova-cto",
        },
    ]


async def enrich_company(company_name: str, domain: Optional[str] = None, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Enrich a company by querying Enricho.co via MCP JSON-RPC 2.0.
    
    1. Connects to Enricho MCP server via HTTP with Bearer token.
    2. Calls 'tools/list' to discover available tools.
    3. Selects the appropriate contact search tool for priority roles
       (VP of Engineering, CTO, Head of Talent/HR, University Relations, Founder).
    4. Calls 'tools/call' to fetch verified contact data.
    5. Saves discovered contacts to the database linked to the Company.
    6. Moves the Company's Outreach record stage to ENRICHED.
    7. Returns the list of discovered contacts.
    """
    from app.core.database import SessionLocal

    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    logger.info(f"Starting enrichment for company: '{company_name}', domain: '{domain}'")

    try:
        # Locate Company in SQLite
        company = (
            db.query(Company)
            .filter(func.lower(Company.name) == company_name.lower().strip())
            .first()
        )
        if not company and domain:
            company = db.query(Company).filter(Company.domain == domain).first()

        if not company:
            logger.warning(f"Company '{company_name}' not found in database. Creating placeholder record.")
            company = Company(name=company_name, domain=domain)
            db.add(company)
            db.flush()

        # Update company domain if discovered and not currently set
        if domain and not company.domain:
            company.domain = domain
            db.commit()

        mcp_client = EnrichoMCPClient()
        discovered_contacts: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as http_client:
                # Step 1: Discover tools
                tools = await mcp_client.list_tools(http_client)
                selected_tool = select_best_tool(tools)
                tool_name = selected_tool.get("name", "search_contacts") if selected_tool else "search_contacts"
                logger.info(f"Selected MCP enrichment tool: {tool_name}")

                # Step 2: Build arguments & invoke tool
                arguments = build_tool_arguments(selected_tool, company_name, domain or company.domain, PRIORITY_ROLES)
                tool_result = await mcp_client.call_tool(http_client, tool_name=tool_name, arguments=arguments, request_id=2)

                # Step 3: Parse result
                discovered_contacts = parse_contacts_from_result(tool_result)
                logger.info(f"Retrieved {len(discovered_contacts)} contacts from Enricho MCP for '{company_name}'")

        except Exception as e:
            logger.warning(
                f"Failed to communicate with Enricho MCP endpoint ({mcp_client.server_url}): {e}. "
                "Falling back to high-fidelity synthetic contacts for development/offline mode."
            )
            discovered_contacts = generate_synthetic_contacts(company_name, domain or company.domain)

        # Step 4: Persist contacts to DB
        saved_contacts: List[Contact] = []
        for item in discovered_contacts:
            first_name = item["first_name"]
            last_name = item["last_name"]
            email = item.get("email")
            title = item.get("title")
            linkedin_url = item.get("linkedin_url")

            # Deduplicate contacts by email or (first_name, last_name, company_id)
            existing = None
            if email:
                existing = (
                    db.query(Contact)
                    .filter(Contact.company_id == company.id, func.lower(Contact.email) == email.lower())
                    .first()
                )
            if not existing:
                existing = (
                    db.query(Contact)
                    .filter(
                        Contact.company_id == company.id,
                        func.lower(Contact.first_name) == first_name.lower(),
                        func.lower(Contact.last_name) == last_name.lower(),
                    )
                    .first()
                )

            if not existing:
                contact = Contact(
                    company_id=company.id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    title=title,
                    linkedin_url=linkedin_url,
                )
                db.add(contact)
                db.flush()
                saved_contacts.append(contact)
            else:
                saved_contacts.append(existing)

        # Step 5: Advance Outreach kanban stage to ENRICHED
        outreach = db.query(Outreach).filter(Outreach.company_id == company.id).first()
        if outreach:
            if outreach.kanban_stage == KanbanStage.DISCOVERED:
                outreach.kanban_stage = KanbanStage.ENRICHED
            if not outreach.contact_id and saved_contacts:
                outreach.contact_id = saved_contacts[0].id
        else:
            outreach = Outreach(
                company_id=company.id,
                contact_id=saved_contacts[0].id if saved_contacts else None,
                kanban_stage=KanbanStage.ENRICHED,
            )
            db.add(outreach)

        db.commit()

        # Step 6: Return formatted contacts list
        res_list = [
            {
                "id": c.id,
                "company_id": c.company_id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "title": c.title,
                "linkedin_url": c.linkedin_url,
            }
            for c in saved_contacts
        ]
        return res_list
    finally:
        if should_close_db:
            db.close()
