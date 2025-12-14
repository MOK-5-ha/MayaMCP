#!/usr/bin/env python3
"""
Test configuration module for Memvid test queries.

This module provides centralized configuration for test queries used across
Memvid-related tests. It includes the existing hardcoded queries and provides
a structured approach for adding additional edge-case queries.

The configuration follows Python best practices with proper type hints,
comprehensive documentation, and extensibility for future test scenarios.
"""

from typing import ClassVar, Dict, List, Tuple, Literal, NewType


# Type aliases for better readability
QueryText = NewType("QueryText", str)
QueryDescription = NewType("QueryDescription", str)
QueryCategory = Literal["basic", "edge_case", "stress_test"]


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

    # Category constants
    CATEGORY_BASIC = "basic"
    CATEGORY_EDGE_CASE = "edge_case"
    CATEGORY_STRESS_TEST = "stress_test"

    # Basic conversational queries - queries that match DEFAULT_DOCUMENTS content
    BASIC_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
        "rough day": (
            "Query expressing emotional difficulty or stress"
        ),
        "patience bartending": (
            "Query about bartending skills and patience"
        ),
    }

    # Edge case queries for boundary testing
    EDGE_CASE_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
        "": "Empty query to test input validation",
        "   ": "Whitespace-only query to test trimming and validation",
        "rough day patience bartending " * 10: (
            "Very long query to test length limits"
        ),
        "Help": "Very short, ambiguous query to test minimal context handling",
        "I need advice on dealing with a rough day at work": (
            "Complex multi-sentence query"
        ),
    }

    # Stress test queries for performance testing
    STRESS_TEST_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
        "I'm having a rough day and could use some patience and understanding from a bartender": (
            "Long, detailed query for stress testing"
        ),
        "I'm dealing with a very challenging day": (
            "Vague query requiring context expansion"
        ),
    }

    # ALL_QUERIES is constructed at module level after class definition
    # to avoid comprehension scope issues with class-level names
    ALL_QUERIES: ClassVar[Dict[QueryText, Tuple[QueryCategory, QueryDescription]]] = {}

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
        valid_categories = [self.CATEGORY_BASIC, self.CATEGORY_EDGE_CASE, self.CATEGORY_STRESS_TEST]
        if category not in valid_categories:
            raise ValueError(
                f"Unknown category: {category}. Must be one of: "
                f"{', '.join(valid_categories)}"
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

    @property
    def queries(self) -> List[QueryText]:
        """
        Get all query texts as a list.

        Returns:
            List of all query texts across all categories
        """
        return self.get_all_queries()


# Construct ALL_QUERIES at module level where class names are resolvable
MemvidTestQueries.ALL_QUERIES = {
    **{query: (MemvidTestQueries.CATEGORY_BASIC, description) for query, description in MemvidTestQueries.BASIC_QUERIES.items()},
    **{query: (MemvidTestQueries.CATEGORY_EDGE_CASE, description) for query, description in MemvidTestQueries.EDGE_CASE_QUERIES.items()},
    **{query: (MemvidTestQueries.CATEGORY_STRESS_TEST, description) for query, description in MemvidTestQueries.STRESS_TEST_QUERIES.items()}
}

# Module-level instance for easy access
memvid_queries = MemvidTestQueries()


# Convenience constants for backward compatibility and easy access
ROUGH_DAY_QUERY: QueryText = "rough day"
PATIENCE_QUERY: QueryText = "patience bartending"

# All basic queries as a list for easy iteration
BASIC_TEST_QUERIES: List[QueryText] = [
    ROUGH_DAY_QUERY,
    PATIENCE_QUERY,
]

# All queries as a list for comprehensive testing
ALL_TEST_QUERIES: List[QueryText] = memvid_queries.get_all_queries()
