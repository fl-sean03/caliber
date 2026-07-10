#!/usr/bin/env python3
"""Search Semantic Scholar API for academic papers."""

import sys
import json
import argparse
import urllib.request
import urllib.parse
from typing import Optional


API_BASE = "https://api.semanticscholar.org/graph/v1"


def search_papers(query: str, limit: int = 10, fields: Optional[str] = None) -> dict:
    """Search for papers by query.

    Args:
        query: Search query string
        limit: Maximum number of results
        fields: Comma-separated list of fields to return

    Returns:
        API response as dictionary
    """
    if fields is None:
        fields = "title,authors,year,abstract,citationCount,url"

    params = {
        'query': query,
        'limit': limit,
        'fields': fields
    }

    url = f"{API_BASE}/paper/search?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    req.add_header('Accept', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {'error': f"URL Error: {e.reason}"}


def get_paper(paper_id: str, fields: Optional[str] = None) -> dict:
    """Get paper by ID.

    Args:
        paper_id: Semantic Scholar paper ID, DOI, or arXiv ID
        fields: Comma-separated list of fields to return

    Returns:
        Paper data as dictionary
    """
    if fields is None:
        fields = "title,authors,year,abstract,citationCount,references,citations,url"

    url = f"{API_BASE}/paper/{paper_id}?fields={fields}"

    req = urllib.request.Request(url)
    req.add_header('Accept', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {'error': f"URL Error: {e.reason}"}


def format_paper(paper: dict) -> str:
    """Format a paper for display."""
    lines = []

    title = paper.get('title', 'No title')
    lines.append(f"Title: {title}")

    authors = paper.get('authors', [])
    if authors:
        author_names = [a.get('name', 'Unknown') for a in authors[:5]]
        if len(authors) > 5:
            author_names.append('et al.')
        lines.append(f"Authors: {', '.join(author_names)}")

    year = paper.get('year')
    if year:
        lines.append(f"Year: {year}")

    citations = paper.get('citationCount')
    if citations is not None:
        lines.append(f"Citations: {citations}")

    url = paper.get('url')
    if url:
        lines.append(f"URL: {url}")

    abstract = paper.get('abstract')
    if abstract:
        # Truncate long abstracts
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
        lines.append(f"Abstract: {abstract}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Search Semantic Scholar')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for papers')
    search_parser.add_argument('query', nargs='+', help='Search query')
    search_parser.add_argument('--limit', '-l', type=int, default=10,
                               help='Number of results (default: 10)')
    search_parser.add_argument('--json', '-j', action='store_true',
                               help='Output as JSON')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get paper by ID')
    get_parser.add_argument('paper_id', help='Paper ID, DOI, or arXiv ID')
    get_parser.add_argument('--json', '-j', action='store_true',
                            help='Output as JSON')

    args = parser.parse_args()

    if args.command == 'search':
        query = ' '.join(args.query)
        result = search_papers(query, limit=args.limit)

        if 'error' in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            papers = result.get('data', [])
            print(f"Found {result.get('total', len(papers))} papers\n")
            for i, paper in enumerate(papers, 1):
                print(f"--- Result {i} ---")
                print(format_paper(paper))
                print()

    elif args.command == 'get':
        result = get_paper(args.paper_id)

        if 'error' in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_paper(result))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
