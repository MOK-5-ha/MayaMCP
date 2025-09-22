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

    # Basic conversational queries - original hardcoded queries
    BASIC_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
                "What about difficult customers?": (
            "Query about handling challenging customer interactions"
        ),
        'I\'m having a rough day': (
            "Query expressing emotional difficulty or stress"
        ),
    }

    # Edge case queries for boundary testing
    EDGE_CASE_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
        "": "Empty query to test input validation",
        "   ": "Whitespace-only query to test trimming and validation",
                "What about difficult customers? " * 10: (
            "Very long query to test length limits"
        ),
        "Help": "Very short, ambiguous query to test minimal context handling",
        "I need advice on dealing with angry clients who won't listen to reason": (
            "Complex multi-sentence query"
        ),
    }

    # Stress test queries for performance testing
    STRESS_TEST_QUERIES: ClassVar[Dict[QueryText, QueryDescription]] = {
        "Can you help me with customer service techniques for handling irate customers who are being unreasonable and difficult to calm down?": (
            "Long, detailed query for stress testing"
        ),
        "I'm dealing with a very challenging customer situation": (
            "Vague query requiring context expansion"
        ),
    }

    # Combined dictionary built once at class definition time (immutable)
    ALL_QUERIES: ClassVar[Dict[QueryText, Tuple[QueryCategory, QueryDescription]]] = {
        **{query: (CATEGORY_BASIC, description) for query, description in BASIC_QUERIES.items()},
        **{query: (CATEGORY_EDGE_CASE, description) for query, description in EDGE_CASE_QUERIES.items()},
        **{query: (CATEGORY_STRESS_TEST, description) for query, description in STRESS_TEST_QUERIES.items()}
    }

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



# Module-level instance for easy access
memvid_queries = MemvidTestQueries()


# Convenience constants for backward compatibility and easy access
DIFFICULT_CUSTOMERS_QUERY: QueryText = "What about difficult customers?"
ROUGH_DAY_QUERY: QueryText = "I\'m having a rough day"

# All basic queries as a list for easy iteration
BASIC_TEST_QUERIES: List[QueryText] = [
    DIFFICULT_CUSTOMERS_QUERY,
    ROUGH_DAY_QUERY,
]

# All queries as a list for comprehensive testing
ALL_TEST_QUERIES: List[QueryText] = memvid_queries.get_all_queries()
