"""Advanced operation nodes for the node editor.

This module provides advanced nodes for regex, file I/O, and HTTP operations.

Op Codes: 110-113

Nodes:
    - RegexMatchNode (110): Pattern matching using regular expressions
    - FileReadNode (111): Read file contents
    - FileWriteNode (112): Write data to file
    - HttpRequestNode (113): Make HTTP requests

Author:
    Michael Economou

Date:
    2025-12-12
"""

import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry


@NodeRegistry.register(110)
class RegexMatchNode(Node):
    r"""Pattern matching using regular expressions.

    Inputs:
        - text (str): Input text to search
        - pattern (str): Regular expression pattern

    Outputs:
        - match (bool): True if pattern matches

    Examples:
        text="hello123", pattern=r"\\d+" -> True
        text="abc", pattern=r"\\d+" -> False

    """

    op_code = 110
    op_title = "Regex Match"
    content_label = "regex"
    content_label_objname = "node_regex_match"

    def __init__(self, scene):
        """Initialize RegexMatchNode with text and pattern inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Match pattern in text using regex."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            self.graphics_node.setToolTip("Connect text input")
            return None

        text = self.inputs[0].getValue()
        if text is None:
            self.mark_invalid()
            self.graphics_node.setToolTip("Text input is empty")
            return None

        text = str(text)

        # Get pattern (default if not connected)
        pattern = ""
        if self.inputs[1].hasEdges():
            pattern_input = self.inputs[1].getValue()
            if pattern_input is not None:
                pattern = str(pattern_input)

        try:
            result = bool(re.search(pattern, text))
            self.markValid()
            self.graphics_node.setToolTip("")
            return result
        except re.error as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Invalid regex pattern: {e}")
            return None


@NodeRegistry.register(111)
class FileReadNode(Node):
    """Read file contents.

    Inputs:
        - filepath (str): Path to file

    Outputs:
        - contents (str): File contents

    Features:
        - UTF-8 encoding
        - Returns file content as string
        - Handles read errors gracefully
    """

    op_code = 111
    op_title = "File Read"
    content_label = "📖"
    content_label_objname = "node_file_read"

    def __init__(self, scene):
        """Initialize FileReadNode with filepath input."""
        super().__init__(scene, self.__class__.op_title, inputs=[5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Read file contents."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            self.graphics_node.setToolTip("Connect filepath input")
            return None

        filepath = self.inputs[0].getValue()
        if filepath is None:
            self.mark_invalid()
            self.graphics_node.setToolTip("Filepath is empty")
            return None

        filepath = str(filepath)

        try:
            # Check if file exists
            if not Path(filepath).exists():
                self.mark_invalid()
                self.graphics_node.setToolTip(f"File not found: {filepath}")
                return None

            # Read file with UTF-8 encoding
            with Path(filepath).open(encoding="utf-8") as f:
                contents = f.read()

            self.markValid()
            self.graphics_node.setToolTip("")
            return contents
        except OSError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"File read error: {e}")
            return None
        except UnicodeDecodeError:
            self.mark_invalid()
            self.graphics_node.setToolTip("File encoding error (not UTF-8)")
            return None


@NodeRegistry.register(112)
class FileWriteNode(Node):
    """Write data to file.

    Inputs:
        - filepath (str): Path to file
        - content (str): Data to write

    Outputs:
        - success (bool): True if write succeeded

    Features:
        - UTF-8 encoding
        - Overwrites existing files
        - Creates directories if needed
        - Handles write errors gracefully
    """

    op_code = 112
    op_title = "File Write"
    content_label = "💾"
    content_label_objname = "node_file_write"

    def __init__(self, scene):
        """Initialize FileWriteNode with filepath and content inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Write content to file."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            self.graphics_node.setToolTip("Connect filepath input")
            return None

        filepath = self.inputs[0].getValue()
        if filepath is None:
            self.mark_invalid()
            self.graphics_node.setToolTip("Filepath is empty")
            return None

        filepath = str(filepath)

        # Get content (default empty string if not connected)
        content = ""
        if self.inputs[1].hasEdges():
            content_input = self.inputs[1].getValue()
            if content_input is not None:
                content = str(content_input)

        try:
            # Create directories if needed
            directory = str(Path(filepath).parent)
            if directory and not Path(directory).exists():
                Path(directory).mkdir(parents=True)

            # Write file with UTF-8 encoding
            with Path(filepath).open("w", encoding="utf-8") as f:
                f.write(content)

            self.markValid()
            self.graphics_node.setToolTip("")
            return True
        except OSError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"File write error: {e}")
            return False
        except PermissionError:
            self.mark_invalid()
            self.graphics_node.setToolTip("Permission denied")
            return False


@NodeRegistry.register(113)
class HttpRequestNode(Node):
    """Make HTTP requests.

    Inputs:
        - url (str): URL to request
        - method (str): HTTP method (GET, POST, PUT, DELETE)

    Outputs:
        - response (str): Response body as string

    Features:
        - Supports GET, POST, PUT, DELETE methods
        - UTF-8 encoding
        - Returns response body
        - Handles network errors gracefully
    """

    op_code = 113
    op_title = "HTTP Request"
    content_label = "🌐"
    content_label_objname = "node_http_request"

    def __init__(self, scene):
        """Initialize HttpRequestNode with url and method inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Make HTTP request."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            self.graphics_node.setToolTip("Connect URL input")
            return None

        url = self.inputs[0].getValue()
        if url is None:
            self.mark_invalid()
            self.graphics_node.setToolTip("URL is empty")
            return None

        url = str(url)

        # Get method (default GET if not connected)
        method = "GET"
        if self.inputs[1].hasEdges():
            method_input = self.inputs[1].getValue()
            if method_input is not None:
                method = str(method_input).upper()

        try:
            # Validate URL starts with http
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Create request
            request = urllib.request.Request(url, method=method)
            request.add_header(
                "User-Agent",
                "node-editor/1.0 (Python)",
            )

            # Make request
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")

            self.markValid()
            self.graphics_node.setToolTip("")
            return body
        except urllib.error.HTTPError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"HTTP Error: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Connection error: {e.reason}")
            return None
        except OSError as e:
            self.mark_invalid()
            self.graphics_node.setToolTip(f"Network error: {e}")
            return None
        except TimeoutError:
            self.mark_invalid()
            self.graphics_node.setToolTip("Request timed out")
            return None
