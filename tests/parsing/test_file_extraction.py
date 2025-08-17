"""Tests for file extraction from JSON data."""

import json
from dataclasses import dataclass

import pytest

from f3_nation_data.parsing.backblast import extract_files_from_json


@dataclass
class JsonFileTestCase:
    json_data: str
    expected_files: list[str] | None
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        JsonFileTestCase(
            json.dumps(
                {
                    'files': [
                        {'url': 'https://example.com/file1.jpg'},
                        {'permalink': 'https://example.com/file2.jpg'},
                        {'url_private': 'https://example.com/file3.jpg'},
                        {'permalink_public': 'https://example.com/file4.jpg'},
                    ],
                },
            ),
            [
                'https://example.com/file1.jpg',
                'https://example.com/file2.jpg',
                'https://example.com/file3.jpg',
                'https://example.com/file4.jpg',
            ],
            'dict_files_with_urls',
        ),
        JsonFileTestCase(
            json.dumps(
                {
                    'files': [
                        'https://example.com/direct1.jpg',
                        'https://example.com/direct2.jpg',
                    ],
                },
            ),
            [
                'https://example.com/direct1.jpg',
                'https://example.com/direct2.jpg',
            ],
            'string_files',
        ),
        JsonFileTestCase(
            json.dumps(
                {
                    'files': [
                        {'url': 'https://example.com/file1.jpg'},
                        'https://example.com/direct.jpg',
                        {'permalink': 'https://example.com/file2.jpg'},
                    ],
                },
            ),
            [
                'https://example.com/file1.jpg',
                'https://example.com/direct.jpg',
                'https://example.com/file2.jpg',
            ],
            'mixed_files',
        ),
        JsonFileTestCase(
            json.dumps(
                {
                    'files': [
                        {'other_field': 'no_url_field'},
                        {'url': 123},  # Non-string URL
                    ],
                },
            ),
            None,
            'invalid_file_objects',
        ),
        JsonFileTestCase(
            json.dumps({'files': []}),
            None,
            'empty_files_list',
        ),
        JsonFileTestCase(
            json.dumps({'files': 'not_a_list'}),
            None,
            'files_not_list',
        ),
        JsonFileTestCase(
            json.dumps({'other_field': 'value'}),
            None,
            'no_files_field',
        ),
        JsonFileTestCase(
            'invalid json string',
            None,
            'invalid_json',
        ),
        JsonFileTestCase(
            json.dumps(
                {
                    'files': [
                        {'url': 'https://example.com/valid.jpg'},
                        {'no_url_fields': 'here'},
                        {'permalink': 'https://example.com/valid2.jpg'},
                    ],
                },
            ),
            [
                'https://example.com/valid.jpg',
                'https://example.com/valid2.jpg',
            ],
            'partial_valid_files',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_files_from_json(tcase: JsonFileTestCase):
    """Test file URL extraction from various JSON formats."""
    result = extract_files_from_json(tcase.json_data)
    assert result == tcase.expected_files
