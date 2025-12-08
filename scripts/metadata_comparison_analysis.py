#!/usr/bin/env python3
"""
Metadata Comparison Analysis Script

This script runs exiftool on all files in C/ExifTest directory in both fast and extended modes,
stores the results in the database, and provides detailed comparison analysis.

Usage: python3 scripts/metadata_comparison_analysis.py
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataComparisonAnalyzer:
    """Analyzes fast vs extended metadata using direct exiftool calls."""

    def __init__(self, test_dir: str = "/mnt/data_1/C/ExifTest"):
        """Initialize with test directory path."""
        self.test_dir = Path(test_dir)
        self.db_path = self._get_analysis_db_path()
        self._setup_analysis_database()

    def _get_analysis_db_path(self) -> Path:
        """Get path for analysis database."""
        data_dir = Path.home() / ".local" / "share" / "oncutf"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "metadata_analysis.db"

    def _setup_analysis_database(self):
        """Setup database for metadata analysis."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Create analysis tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    file_size INTEGER,
                    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_fast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    key_count INTEGER NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES file_analysis (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_extended (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    key_count INTEGER NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES file_analysis (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_comparison (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    fast_only_keys TEXT,  -- JSON array
                    extended_only_keys TEXT,  -- JSON array
                    common_keys TEXT,  -- JSON array
                    value_differences TEXT,  -- JSON object
                    analysis_summary TEXT,  -- JSON object
                    FOREIGN KEY (file_id) REFERENCES file_analysis (id)
                )
            """)

            conn.commit()
            logger.info(f"Analysis database initialized: {self.db_path}")

    def run_exiftool_fast(self, file_path: str) -> dict[str, Any]:
        """Run exiftool in fast mode (standard extraction)."""
        try:
            cmd = [
                'exiftool',
                '-json',
                '-charset', 'filename=UTF8',
                str(file_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"ExifTool fast mode failed for {file_path}: {result.stderr}")
                return {}

            data = json.loads(result.stdout)
            return data[0] if data else {}

        except Exception as e:
            logger.error(f"Error running exiftool fast mode on {file_path}: {e}")
            return {}

    def run_exiftool_extended(self, file_path: str) -> dict[str, Any]:
        """Run exiftool in extended mode (-ee flag for embedded metadata)."""
        try:
            cmd = [
                'exiftool',
                '-json',
                '-ee',  # Extract embedded data
                '-charset', 'filename=UTF8',
                str(file_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=60  # Extended mode takes longer
            )

            if result.returncode != 0:
                logger.warning(f"ExifTool extended mode failed for {file_path}: {result.stderr}")
                return {}

            data = json.loads(result.stdout)

            # Extended mode can return multiple objects (embedded data)
            if not data:
                return {}

            # Merge all objects into one (like our UnifiedMetadataManager does)
            result_dict = data[0].copy()
            if len(data) > 1:
                for i, extra in enumerate(data[1:], start=1):
                    for key, value in extra.items():
                        new_key = f"[Segment {i}] {key}"
                        result_dict[new_key] = value

            # Mark as extended
            result_dict["__extended__"] = True
            return result_dict

        except Exception as e:
            logger.error(f"Error running exiftool extended mode on {file_path}: {e}")
            return {}

    def analyze_file(self, file_path: Path) -> int:
        """Analyze a single file and store results in database."""
        logger.info(f"Analyzing file: {file_path.name}")

        # Get file info
        try:
            file_size = file_path.stat().st_size
        except:
            file_size = 0

        file_extension = file_path.suffix.lower()

        # Store file info
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_analysis (file_path, file_extension, file_size)
                VALUES (?, ?, ?)
            """, (str(file_path), file_extension, file_size))
            file_id = cursor.lastrowid
            conn.commit()

        # Extract metadata in both modes
        fast_metadata = self.run_exiftool_fast(file_path)
        extended_metadata = self.run_exiftool_extended(file_path)

        # Store metadata
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Store fast metadata
            if fast_metadata:
                cursor.execute("""
                    INSERT INTO metadata_fast (file_id, metadata_json, key_count)
                    VALUES (?, ?, ?)
                """, (file_id, json.dumps(fast_metadata), len(fast_metadata)))

            # Store extended metadata
            if extended_metadata:
                cursor.execute("""
                    INSERT INTO metadata_extended (file_id, metadata_json, key_count)
                    VALUES (?, ?, ?)
                """, (file_id, json.dumps(extended_metadata), len(extended_metadata)))

            conn.commit()

        # Compare metadata
        self._compare_metadata(file_id, fast_metadata, extended_metadata)

        return file_id

    def _compare_metadata(self, file_id: int, fast_data: dict[str, Any], extended_data: dict[str, Any]) -> None:
        """Compare fast and extended metadata and store analysis."""

        # Clean internal markers for comparison
        fast_clean = {k: v for k, v in fast_data.items() if not k.startswith('__')}
        extended_clean = {k: v for k, v in extended_data.items() if not k.startswith('__')}

        fast_keys = set(fast_clean.keys())
        extended_keys = set(extended_clean.keys())

        # Analyze key differences
        fast_only = list(fast_keys - extended_keys)
        extended_only = list(extended_keys - fast_keys)
        common_keys = list(fast_keys & extended_keys)

        # Analyze value differences for common keys
        value_differences = {}
        for key in common_keys:
            fast_val = fast_clean[key]
            extended_val = extended_clean[key]

            if fast_val != extended_val:
                value_differences[key] = {
                    'fast': fast_val,
                    'extended': extended_val
                }

        # Create analysis summary
        analysis_summary = {
            'fast_key_count': len(fast_keys),
            'extended_key_count': len(extended_keys),
            'common_key_count': len(common_keys),
            'fast_only_count': len(fast_only),
            'extended_only_count': len(extended_only),
            'value_differences_count': len(value_differences),
            'identical_keys': len(common_keys) - len(value_differences)
        }

        # Store comparison results
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO metadata_comparison
                (file_id, fast_only_keys, extended_only_keys, common_keys, value_differences, analysis_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                json.dumps(fast_only),
                json.dumps(extended_only),
                json.dumps(common_keys),
                json.dumps(value_differences),
                json.dumps(analysis_summary)
            ))
            conn.commit()

    def analyze_all_files(self):
        """Analyze all files in the test directory."""
        logger.info(f"Starting analysis of all files in: {self.test_dir}")

        if not self.test_dir.exists():
            logger.error(f"Test directory does not exist: {self.test_dir}")
            return

        # Get all files (excluding .THM which are thumbnails)
        files = [f for f in self.test_dir.iterdir()
                if f.is_file() and f.suffix.lower() != '.thm']

        logger.info(f"Found {len(files)} files to analyze")

        for i, file_path in enumerate(files, 1):
            logger.info(f"[{i}/{len(files)}] Analyzing: {file_path.name}")
            try:
                self.analyze_file(file_path)
            except Exception as e:
                logger.error(f"Failed to analyze {file_path.name}: {e}")

        logger.info("Analysis complete!")

    def generate_report(self):
        """Generate comprehensive comparison report."""
        logger.info("Generating comparison report...")

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get summary statistics
            cursor.execute("""
                SELECT
                    fa.file_extension,
                    COUNT(*) as file_count,
                    AVG(json_extract(mc.analysis_summary, '$.fast_key_count')) as avg_fast_keys,
                    AVG(json_extract(mc.analysis_summary, '$.extended_key_count')) as avg_extended_keys,
                    AVG(json_extract(mc.analysis_summary, '$.value_differences_count')) as avg_differences
                FROM file_analysis fa
                JOIN metadata_comparison mc ON fa.id = mc.file_id
                GROUP BY fa.file_extension
                ORDER BY fa.file_extension
            """)

            print("\n" + "="*80)
            print("METADATA COMPARISON ANALYSIS REPORT")
            print("="*80)

            print(f"\n SUMMARY BY FILE TYPE:")
            print(f"{'Extension':<10} {'Files':<6} {'Avg Fast':<10} {'Avg Extended':<12} {'Avg Diff':<10}")
            print("-" * 60)

            for row in cursor.fetchall():
                ext = row['file_extension'] or 'none'
                print(f"{ext:<10} {row['file_count']:<6} {row['avg_fast_keys']:<10.1f} {row['avg_extended_keys']:<12.1f} {row['avg_differences']:<10.1f}")

            # Get detailed analysis for files with significant differences
            cursor.execute("""
                SELECT
                    fa.file_path,
                    fa.file_extension,
                    mc.analysis_summary,
                    mc.value_differences
                FROM file_analysis fa
                JOIN metadata_comparison mc ON fa.id = mc.file_id
                WHERE json_extract(mc.analysis_summary, '$.value_differences_count') > 0
                   OR json_extract(mc.analysis_summary, '$.extended_only_count') > 10
                ORDER BY json_extract(mc.analysis_summary, '$.value_differences_count') DESC
            """)

            print(f"\n FILES WITH SIGNIFICANT DIFFERENCES:")

            for row in cursor.fetchall():
                filename = Path(row['file_path']).name
                analysis = json.loads(row['analysis_summary'])
                print(f"\n {filename} ({row['file_extension']})")
                print(f"   Fast: {analysis['fast_key_count']} keys | Extended: {analysis['extended_key_count']} keys")
                print(f"   Extended-only: {analysis['extended_only_count']} | Value differences: {analysis['value_differences_count']}")

                if analysis['value_differences_count'] > 0:
                    value_diffs = json.loads(row['value_differences'])
                    print(f"   Key differences:")
                    for key, diff in list(value_diffs.items())[:5]:  # Show first 5
                        print(f"     {key}: '{diff['fast']}' vs '{diff['extended']}'")
                    if len(value_diffs) > 5:
                        print(f"     ... and {len(value_diffs) - 5} more")

        print(f"\n Analysis database saved to: {self.db_path}")
        print("="*80)


def main():
    """Main function to run the analysis."""
    print(" Starting Comprehensive Metadata Analysis")
    print("This will analyze fast vs extended metadata for all files in C/ExifTest")

    analyzer = MetadataComparisonAnalyzer()

    # Run the analysis
    analyzer.analyze_all_files()

    # Generate report
    analyzer.generate_report()

    print("\n Analysis complete!")


if __name__ == "__main__":
    main()
