"""OLS MCP Server using fastmcp.

This module provides MCP tools for interacting with the Ontology Lookup Service (OLS) API.
"""
from .models import OntologyInfo, OntologySearchResponse, TermSearchResponse, DetailedTermInfo
import json
import urllib.parse
import sys
import argparse
from typing import Any, Optional, Annotated

import httpx
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("OLS MCP Server")

# Base URL for OLS API
OLS_BASE_URL = "https://www.ebi.ac.uk/ols4"

# HTTP client for making requests
client = httpx.AsyncClient(timeout=30.0)


def url_encode_iri(iri: str) -> str:
    """Double URL encode an IRI as required by OLS API."""
    return urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")


def format_response(data: Any, max_items: int = 10) -> str:
    """Format API response data for display."""
    if isinstance(data, dict):
        if "elements" in data:
            # Handle paginated response
            elements = data["elements"][:max_items]
            total = data.get("totalElements", len(elements))
            
            result = []
            for item in elements:
                if isinstance(item, dict):
                    # Extract key fields for display
                    label = item.get("label", "")
                    iri = item.get("iri", "")
                    description = item.get("description", [])
                    if isinstance(description, list) and description:
                        description = description[0]
                    elif isinstance(description, list):
                        description = ""
                    
                    result.append({
                        "label": label,
                        "iri": iri,
                        "description": description[:200] + "..." if len(str(description)) > 200 else description
                    })
            
            return json.dumps({
                "items": result,
                "total_items": total,
                "showing": len(result)
            }, indent=2)
        else:
            # Single item response
            return json.dumps(data, indent=2)
    
    return json.dumps(data, indent=2)


@mcp.tool()
async def search_terms(
    query: Annotated[str, "Search query text"],
    ontology: Annotated[Optional[str], "Optional ontology ID to restrict search (e.g., 'efo', 'go', 'hp'); may be a list of IDs separated by commas"] = None,
    exact_match: Annotated[bool, "Whether to perform exact matching"] = False,
    include_obsolete: Annotated[bool, "Include obsolete terms in results"] = False,
    rows: Annotated[int, "Maximum number of results to return"] = 10
) -> TermSearchResponse | str:
    """Search for terms across ontologies using the OLS search API."""
    params = {
        "q": query,
        "rows": rows,
        "start": 0,
        "exact": exact_match,
        "obsoletes": include_obsolete
    }
    
    if ontology:
        params["ontology"] = ontology
    
    url = f"{OLS_BASE_URL}/api/search"
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "response" in data and "docs" in data["response"]:
            # Transform legacy API format
            docs = data["response"]["docs"]
            result = {
                "elements": docs,
                "totalElements": data["response"].get("numFound", len(docs))
            }
            return format_response(result, rows)
        
        return format_response(data, rows)
        
    except httpx.HTTPError as e:
        return f"Error searching terms: {str(e)}"


@mcp.tool()
async def get_ontology_info(
    ontology_id: Annotated[str, "Ontology identifier (e.g., 'efo', 'go', 'mondo')"]
) -> OntologyInfo | str:
    """Get detailed information about a specific ontology."""
    url = f"{OLS_BASE_URL}/api/v2/ontologies/{ontology_id}"
    
    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return OntologyInfo.model_validate(data)
        
    except httpx.HTTPError as e:
        return f"Error getting ontology info: {str(e)}"


@mcp.tool()
async def search_ontologies(
    search: Annotated[Optional[str], "Optional search query to filter ontologies"] = None,
    page: Annotated[int, "Page number for pagination (default: 0)"] = 0,
    size: Annotated[int, "Number of results per page (default: 20)"] = 20,
) -> list[OntologySearchResponse] | str:
    """Search for available ontologies."""
    params: dict[str, Any] = {
        "page": page,
        "size": size
    }
    
    if search:
        params["search"] = search
    
    url = f"{OLS_BASE_URL}/api/v2/ontologies"
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return format_response(data, size)
        
    except httpx.HTTPError as e:
        return f"Error searching ontologies: {str(e)}"


@mcp.tool()
async def get_term_info(
    id: Annotated[
        str, 
        ("Can be the IRI (Example : http://purl.obolibrary.org/obo/DUO_0000017)"
         ", short form (Example : DUO_0000017), or obo ID (Example: DUO:0000017) of the term")
    ],
) -> DetailedTermInfo | str:
    """Get detailed information about a specific term."""
    
    url = f"{OLS_BASE_URL}/api/terms"
    
    try:
        response = await client.get(url, params={"id": id})
        response.raise_for_status()
        data = response.json()
        embedded = data.get("_embedded", {})
        if "terms" in embedded:
            terms = embedded["terms"]
            return DetailedTermInfo.model_validate(terms[0])
        return f"Term with ID '{id}' not found in OLS."
        
    except httpx.HTTPError as e:
        return f"Error getting term info: {str(e)}"

###

@mcp.tool()
async def get_term_children(
    term_iri: str,
    ontology: str,
    include_obsolete: bool = False,
    size: int = 20
) -> str:
    """Get direct children of a specific term.
    
    Args:
        term_iri: The IRI of the term
        ontology: The ontology identifier
        include_obsolete: Include obsolete entities
        size: Maximum number of results
    
    Returns:
        JSON formatted list of child terms
    """
    encoded_iri = url_encode_iri(term_iri)
    
    params: dict[str, Any] = {
        "page": 0,
        "size": size,
        "includeObsoleteEntities": include_obsolete
    }
    
    url = f"{OLS_BASE_URL}/api/v2/ontologies/{ontology}/classes/{encoded_iri}/children"
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return format_response(data, size)
        
    except httpx.HTTPError as e:
        return f"Error getting term children: {str(e)}"
    
    
@mcp.tool()
async def get_term_ancestors(
    term_iri: str,
    ontology: str,
    include_obsolete: bool = False,
    size: int = 20
) -> str:
    """Get ancestor terms (parents) of a specific term.
    
    Args:
        term_iri: The IRI of the term
        ontology: The ontology identifier
        include_obsolete: Include obsolete entities
        size: Maximum number of results
    
    Returns:
        JSON formatted list of ancestor terms
    """
    encoded_iri = url_encode_iri(term_iri)
    
    params: dict[str, Any] = {
        "page": 0,
        "size": size,
        "includeObsoleteEntities": include_obsolete
    }
    
    url = f"{OLS_BASE_URL}/api/v2/ontologies/{ontology}/classes/{encoded_iri}/ancestors"
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return format_response(data, size)
        
    except httpx.HTTPError as e:
        return f"Error getting term ancestors: {str(e)}"


@mcp.tool()
async def find_similar_terms(
    term_iri: str,
    ontology: str,
    size: int = 10
) -> str:
    """Find terms similar to the given term using LLM embeddings.
    
    Args:
        term_iri: The IRI of the reference term
        ontology: The ontology identifier
        size: Maximum number of similar terms to return
    
    Returns:
        JSON formatted list of similar terms
    """
    encoded_iri = url_encode_iri(term_iri)
    
    params: dict[str, Any] = {
        "page": 0,
        "size": size
    }
    
    url = f"{OLS_BASE_URL}/api/v2/ontologies/{ontology}/classes/{encoded_iri}/llm_similar"
    
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return format_response(data, size)
        
    except httpx.HTTPError as e:
        return f"Error finding similar terms: {str(e)}"



if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="OLS MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print("Debug mode enabled", file=sys.stderr)
    
    # Run in stdio mode (default for MCP)
    mcp.run()


def main():
    """Entry point for the MCP server (stdio mode by default)."""
    mcp.run()


def main_debug():
    """Entry point for debug mode."""
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)
    print("OLS MCP Server - Debug mode enabled", file=sys.stderr)
    mcp.run()
