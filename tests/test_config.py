#!/usr/bin/env python3
"""
Test configuration module for Memvid test queries.

This module provides centralized configuration for test queries used across
Memvid-related tests. It includes the existing hardcoded queries and provides
a structured approach for adding additional edge-case queries.

The configuration follows Python best practices with proper type hints,
comprehensive documentation, and extensibility for future test scenarios.
"""

from typing import Dict, List, Tuple


# Type aliases for better readability
QueryText = str
QueryDescription = str
QueryCategory = str


class MemvidTestQueries:
    """
    Configuration class for Memvid test queries.

    This class provides a centralized location for all test queries used in
    Memvid-related tests. It includes the original hardcoded queries and
    provides a clear structure for adding additional edge-case queries.

    Attributes:
        BASIC_QUERIES: Basic conversational queries for standard testing
        EDGE_CASE_QUERIES: Edge case queries for boundary testing
        STRESS_TEST_QUERIES: Complex queries for stress testing
        ALL_QUERIES: Combined dictionary of all query categories
    """

    # Basic conversational queries - original hardcoded queries
    BASIC_QUERIES: Dict[QueryText, QueryDescription] = {
                "What about difficult customers?": (
            "Query about handling challenging customer interactions"
        ),
                "I\'m having a rough day": (
            "Query expressing emotional difficulty or stress"
        ),
    }

    # Edge case queries for boundary testing
    EDGE_CASE_QUERIES: Dict[QueryText, QueryDescription] = {
        "": "Empty query to test input validation",
        "   ": "Whitespace-only query to test trimming and validation",
                "What about difficult customers? " * 10: (
            "Very long query to test length limits"
        ),
        "Help": "Very short, ambiguous query to test minimal context handling",
                "I need advice on dealing with angry clients who won\'t listen to reason": (
            "Complex multi-sentence query"
        ),
    }

    # Stress test queries for performance testing
    STRESS_TEST_QUERIES: Dict[QueryText, QueryDescription] = {
                "Can you help me with customer service techniques for handling irate "
        "customers who are being unreasonable and difficult to calm down?": (
            "Long, detailed query for stress testing"
        ),
                "I\'m dealing with a very challenging customer situation": (
            "Vague query requiring context expansion"
        ),
    }

    # Combined dictionary for easy access to all queries
    ALL_QUERIES: Dict[QueryText, Tuple[QueryCategory, QueryDescription]] = {}

    def __init__(self) -> None:
        """Initialize the combined queries dictionary."""
        # Populate the combined dictionary
        for query, description in self.BASIC_QUERIES.items():
            self.ALL_QUERIES[query] = ("basic", description)

        for query, description in self.EDGE_CASE_QUERIES.items():
            self.ALL_QUERIES[query] = ("edge_case", description)

        for query, description in self.STRESS_TEST_QUERIES.items():
            self.ALL_QUERIES[query] = ("stress_test", description)

    def get_queries_by_category(
        self, category: QueryCategory
    ) -> Dict[QueryText, QueryDescription]:
        """
        Get all queries for a specific category.

        Args:
            category: The category of queries to retrieve
                      (must be one of: basic, edge_case, stress_test)

        Returns:
            Dictionary of queries and their descriptions for the specified
            category

        Raises:
            ValueError: If the category is not recognized
        """
        if category not in ["basic", "edge_case", "stress_test"]:
            raise ValueError(
                f"Unknown category: {category}. Must be one of: basic, "
                "edge_case, stress_test"
            )

        return {
            query: description
            for query, (cat, description) in self.ALL_QUERIES.items()
            if cat == category
        }
    def get_all_queries(self) -> List[QueryText]:
        """
        Get all query texts as a list.

        Returns:
            List of all query texts across all categories
        """
        return list(self.ALL_QUERIES.keys())



# Module-level instance for easy access
memvid_queries = MemvidTestQueries()


# Convenience constants for backward compatibility and easy access
DIFFICULT_CUSTOMERS_QUERY: QueryText = "What about difficult customers?"
ROUGH_DAY_QUERY: QueryText = "I'm having a rough day"

# All basic queries as a list for easy iteration
BASIC_TEST_QUERIES: List[QueryText] = [
    DIFFICULT_CUSTOMERS_QUERY,
    ROUGH_DAY_QUERY,
]

# All queries as a list for comprehensive testing
ALL_TEST_QUERIES: List[QueryText] = memvid_queries.get_all_queries()