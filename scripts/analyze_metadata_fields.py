#!/usr/bin/env python3
"""
Metadata Field Analysis Script

This script analyzes actual files to understand:
1. What metadata fields are returned by exiftool
2. Differences between fast (-json) and extended (-json -ee) modes
3. Field distribution by file type
4. Manufacturer-specific fields

Usage:
    python scripts/analyze_metadata_fields.py <file_or_directory>
"""

import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


class MetadataAnalyzer:
    """Analyzes metadata fields from real files."""

    def __init__(self):
        self.results = defaultdict(lambda: {
            'fast_fields': Counter(),
            'extended_fields': Counter(),
            'fast_only': set(),
            'extended_only': set(),
            'samples': []
        })

    def check_exiftool_available(self) -> bool:
        """Check if exiftool is available."""
        try:
            result = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f" ExifTool version: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        print(" ExifTool not found. Please install it:")
        print("   Ubuntu/Debian: sudo apt install libimage-exiftool-perl")
        print("   macOS: brew install exiftool")
        return False


    def get_metadata_fast(self, file_path: Path) -> tuple[dict, float]:
        """Get metadata using fast mode (-json)."""
        start = time.perf_counter()
        try:
            result = subprocess.run(
                ['exiftool', '-json', '-charset', 'filename=UTF8', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            elapsed = time.perf_counter() - start

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data[0] if data else {}, elapsed
        except Exception as e:
            print(f"️  Fast mode error for {file_path.name}: {e}")

        return {}, 0.0

    def get_metadata_extended(self, file_path: Path) -> tuple[dict, float]:
        """Get metadata using extended mode (-json -ee)."""
        start = time.perf_counter()
        try:
            result = subprocess.run(
                ['exiftool', '-json', '-ee', '-charset', 'filename=UTF8', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            elapsed = time.perf_counter() - start

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data[0] if data else {}, elapsed
        except Exception as e:
            print(f"️  Extended mode error for {file_path.name}: {e}")

        return {}, 0.0

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single file."""
        if not file_path.is_file():
            return

        # Skip very large files
        if file_path.stat().st_size > 100 * 1024 * 1024:  # 100MB
            print(f"⏭️  Skipping large file: {file_path.name}")
            return

        print(f"\n{'='*80}")
        print(f" Analyzing: {file_path.name}")
        print(f"   Size: {file_path.stat().st_size / 1024:.1f} KB")
        # Get fast metadata
        fast_data, fast_time = self.get_metadata_fast(file_path)
        if not fast_data:
            print("    No metadata returned")
            return
        file_type = fast_data.get('FileType', 'Unknown')
        mime_type = fast_data.get('MIMEType', 'Unknown')
        make = fast_data.get('Make', 'Unknown')
        print(f"   Type: {file_type} ({mime_type})")
        print(f"   Make: {make}")
        # Get extended metadata
        extended_data, extended_time = self.get_metadata_extended(file_path)
        # Analyze fields
        fast_fields = set(fast_data.keys())
        extended_fields = set(extended_data.keys())
        fast_only = fast_fields - extended_fields
        extended_only = extended_fields - fast_fields
        common = fast_fields & extended_fields
        print(f"\n    Fast mode: {len(fast_fields)} fields in {fast_time*1000:.1f}ms")
        print(f"    Extended mode: {len(extended_fields)} fields in {extended_time*1000:.1f}ms")
        print(f"    Common: {len(common)} | Fast-only: {len(fast_only)} | Extended-only: {len(extended_only)}")
        if extended_time > 0:
            speedup = extended_time / fast_time if fast_time > 0 else 0
            print(f"   ⏱️  Extended is {speedup:.1f}x slower")

        # Store results by category
        category = self._categorize_file(file_type, mime_type)
        self.results[category]['fast_fields'].update(fast_fields)
        self.results[category]['extended_fields'].update(extended_fields)
        self.results[category]['fast_only'].update(fast_only)
        self.results[category]['extended_only'].update(extended_only)

        # Store sample with detailed info
        sample = {
            'filename': file_path.name,
            'file_type': file_type,
            'mime_type': mime_type,
            'make': make,
            'fast_field_count': len(fast_fields),
            'extended_field_count': len(extended_fields),
            'fast_time_ms': fast_time * 1000,
            'extended_time_ms': extended_time * 1000,
            'fast_fields_sample': list(fast_fields)[:20],  # First 20
            'extended_only_fields': list(extended_only)[:10] if extended_only else []
        }
        self.results[category]['samples'].append(sample)

        # Show interesting fields
        self._show_interesting_fields(file_type, make, fast_data, extended_data)

    def _categorize_file(self, _file_type: str, mime_type: str) -> str:
        """Categorize file based on type."""
        mime_lower = mime_type.lower()

        if 'image' in mime_lower:
            return 'Image'
        elif 'video' in mime_lower:
            return 'Video'
        elif 'audio' in mime_lower:
            return 'Audio'
        elif 'pdf' in mime_lower or 'document' in mime_lower:
            return 'Document'
        else:
            return 'Other'

    def _show_interesting_fields(self, _file_type: str, make: str,
                                  fast_data: dict, extended_data: dict) -> None:
        """Show interesting fields for this file type."""
        # Rename-relevant fields
        rename_fields = [
            'DateTimeOriginal', 'CreateDate', 'ModifyDate',
            'Make', 'Model', 'LensModel',
            'ISO', 'FNumber', 'ExposureTime', 'FocalLength',
            'ImageWidth', 'ImageHeight', 'Orientation',
            'Title', 'Description', 'Artist', 'Copyright',
            'Duration', 'FrameRate', 'VideoCodec',
            'Album', 'Genre', 'TrackNumber'
        ]

        found_rename = {k: v for k, v in fast_data.items() if k in rename_fields}
        if found_rename:
            print("\n    Rename-relevant fields found:")
            for k, v in list(found_rename.items())[:10]:
                print(f"      {k}: {str(v)[:60]}")

        # Manufacturer-specific fields
        if make != 'Unknown':
            make_prefix = make.split()[0]  # Canon, Sony, Nikon, etc.
            make_fields = {k: v for k, v in fast_data.items()
                          if make_prefix.lower() in k.lower()}

            if make_fields:
                print(f"\n   ️  {make} specific fields ({len(make_fields)}):")
                for k in list(make_fields.keys())[:5]:
                    print(f"      {k}")

        # Extended-only interesting fields
        extended_only = set(extended_data.keys()) - set(fast_data.keys())
        if extended_only:
            print(f"\n    Extended-only fields ({len(extended_only)}):")
            for k in list(extended_only)[:10]:
                print(f"      {k}")

    def scan_directory(self, directory: Path, max_files: int = 20) -> None:
        """Scan directory for sample files."""
        print(f"\n Scanning directory: {directory}")

        # Common extensions by category
        extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.arw'],
            'video': ['.mp4', '.mov', '.avi', '.mkv', '.m4v'],
            'audio': ['.mp3', '.flac', '.wav', '.m4a', '.aac'],
            'document': ['.pdf', '.docx', '.doc']
        }

        # Find sample files
        files_by_type = defaultdict(list)

        for ext_list in extensions.values():
            for ext in ext_list:
                files_by_type[ext].extend(list(directory.rglob(f'*{ext}'))[:3])

        # Analyze files
        count = 0
        for _ext, files in files_by_type.items():
            for file_path in files:
                if count >= max_files:
                    break
                self.analyze_file(file_path)
                count += 1

    def print_summary(self) -> None:
        """Print summary of findings."""
        print(f"\n\n{'='*80}")
        print(" SUMMARY OF FINDINGS")
        print(f"{'='*80}")

        for category, data in sorted(self.results.items()):
            samples = data['samples']
            if not samples:
                continue

            print(f"\n{'─'*80}")
            print(f" {category} Files ({len(samples)} analyzed)")
            print(f"{'─'*80}")

            # Average field counts
            avg_fast = sum(s['fast_field_count'] for s in samples) / len(samples)
            avg_extended = sum(s['extended_field_count'] for s in samples) / len(samples)
            avg_fast_time = sum(s['fast_time_ms'] for s in samples) / len(samples)
            avg_extended_time = sum(s['extended_time_ms'] for s in samples) / len(samples)

            print("\n   Average Fields:")
            print(f"      Fast mode: {avg_fast:.0f} fields in {avg_fast_time:.1f}ms")
            print(f"      Extended mode: {avg_extended:.0f} fields in {avg_extended_time:.1f}ms")
            print(f"      Extended overhead: {avg_extended - avg_fast:.0f} extra fields, {avg_extended_time - avg_fast_time:.1f}ms slower")

            # Most common fields
            common_fast = data['fast_fields'].most_common(20)
            print("\n    Most Common Fast Fields (top 20):")
            for field, count in common_fast:
                print(f"      {field}: {count}/{len(samples)} files")

            # Extended-only fields
            if data['extended_only']:
                print(f"\n    Extended-Only Fields ({len(data['extended_only'])}):")
                for field in list(data['extended_only'])[:15]:
                    print(f"      {field}")

            # Manufacturers found
            makes = {s['make'] for s in samples if s['make'] != 'Unknown'}
            if makes:
                print(f"\n   ️  Manufacturers found: {', '.join(sorted(makes))}")

        # Recommendations
        print(f"\n\n{'='*80}")
        print(" RECOMMENDATIONS")
        print(f"{'='*80}")

        for category, data in sorted(self.results.items()):
            if not data['samples']:
                continue

            # Get fields that appear in >50% of files
            common = {field for field, count in data['fast_fields'].items()
                     if count >= len(data['samples']) * 0.5}

            print(f"\n{category} Essential Fields ({len(common)}):")
            for field in sorted(common)[:30]:
                print(f"   -{field}")

    def export_results(self, output_file: Path) -> None:
        """Export results to JSON file."""
        export_data = {}

        for category, data in self.results.items():
            export_data[category] = {
                'sample_count': len(data['samples']),
                'fast_fields': list(data['fast_fields'].keys()),
                'extended_fields': list(data['extended_fields'].keys()),
                'fast_only': list(data['fast_only']),
                'extended_only': list(data['extended_only']),
                'samples': data['samples']
            }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"\n Results exported to: {output_file}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_metadata_fields.py <file_or_directory>")
        print("\nExamples:")
        print("  python scripts/analyze_metadata_fields.py /path/to/photo.jpg")
        print("  python scripts/analyze_metadata_fields.py /path/to/photos/")
        print("  python scripts/analyze_metadata_fields.py ~/Pictures/")
        sys.exit(1)

    analyzer = MetadataAnalyzer()

    # Check exiftool
    if not analyzer.check_exiftool_available():
        sys.exit(1)

    # Analyze path
    path = Path(sys.argv[1]).expanduser()

    if not path.exists():
        print(f" Path not found: {path}")
        sys.exit(1)

    if path.is_file():
        analyzer.analyze_file(path)
    elif path.is_dir():
        max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        analyzer.scan_directory(path, max_files)

    # Print summary
    analyzer.print_summary()

    # Export results
    output_file = Path(__file__).parent.parent / 'reports' / 'metadata_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    analyzer.export_results(output_file)


if __name__ == '__main__':
    main()

