"""Time and date manipulation nodes for the node editor.

This module provides nodes for working with timestamps, dates, and time-related operations.
All timestamps are Unix timestamps (seconds since epoch, 1970-01-01 UTC).

Op Codes: 100-109

Nodes:
    - CurrentTimeNode (100): Returns current timestamp
    - FormatDateNode (101): Format timestamp to string
    - ParseDateNode (102): Parse date string to timestamp
    - TimeDeltaNode (103): Add/subtract time offset to timestamp
    - CompareTimeNode (104): Compare two timestamps

Author:
    Michael Economou

Date:
    2025-12-12
"""

from datetime import UTC, datetime

from oncutf.ui.widgets.node_editor.core.node import Node
from oncutf.ui.widgets.node_editor.core.socket import LEFT_CENTER, RIGHT_CENTER
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry


@NodeRegistry.register(100)
class CurrentTimeNode(Node):
    """Returns the current system time as a Unix timestamp.

    Outputs:
        - Float timestamp (seconds since epoch, UTC)

    Example:
        Output: 1702376400.123456 (represents 2024-12-12 12:00:00.123456 UTC)

    """

    op_code = 100
    op_title = "Current Time"
    content_label = "Now"
    content_label_objname = "node_current_time"

    def __init__(self, scene):
        """Initialize CurrentTimeNode with no inputs and timestamp output."""
        super().__init__(scene, self.__class__.op_title, inputs=[], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Return the current system timestamp."""
        return datetime.now(UTC).timestamp()


@NodeRegistry.register(101)
class FormatDateNode(Node):
    """Format a Unix timestamp into a human-readable date/time string.

    Inputs:
        - timestamp (float): Unix timestamp to format
        - format (str): Format string (Python strftime format)

    Outputs:
        - formatted (str): Formatted date/time string

    Format Examples:
        "%Y-%m-%d" -> "2024-12-31"
        "%Y-%m-%d %H:%M:%S" -> "2024-12-31 15:30:45"
        "%B %d, %Y" -> "December 31, 2024"
    """

    op_code = 101
    op_title = "Format Date"
    content_label = "fmt"
    content_label_objname = "node_format_date"

    def __init__(self, scene):
        """Initialize FormatDateNode with timestamp and format inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Format timestamp according to format string."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            return None

        timestamp = self.inputs[0].getValue()
        if timestamp is None:
            self.mark_invalid()
            return None

        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            self.mark_invalid()
            return None

        # Get format string (default if not connected)
        format_str = "%Y-%m-%d %H:%M:%S"
        if self.inputs[1].hasEdges():
            format_input = self.inputs[1].getValue()
            if format_input is not None:
                format_str = str(format_input)

        try:
            dt = datetime.fromtimestamp(timestamp, tz=UTC).astimezone()
            result = dt.strftime(format_str)
            self.markValid()
        except (ValueError, OSError):
            self.mark_invalid()
            return None
        else:
            return result


@NodeRegistry.register(102)
class ParseDateNode(Node):
    """Parse a date/time string into a Unix timestamp.

    Inputs:
        - date_string (str): Date/time string to parse
        - format (str): Format string matching the input

    Outputs:
        - timestamp (float): Unix timestamp in seconds

    Format Examples:
        "2024-12-12" with "%Y-%m-%d"
        "2024-12-12 15:30:45" with "%Y-%m-%d %H:%M:%S"
    """

    op_code = 102
    op_title = "Parse Date"
    content_label = "parse"
    content_label_objname = "node_parse_date"

    def __init__(self, scene):
        """Initialize ParseDateNode with string and format inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Parse date string to timestamp."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            return None

        date_string = self.inputs[0].getValue()
        if date_string is None:
            self.mark_invalid()
            return None

        date_string = str(date_string)

        # Get format string (default if not connected)
        format_str = "%Y-%m-%d %H:%M:%S"
        if self.inputs[1].hasEdges():
            format_input = self.inputs[1].getValue()
            if format_input is not None:
                format_str = str(format_input)

        try:
            dt = datetime.strptime(date_string, format_str).replace(tzinfo=UTC)
            result = dt.timestamp()
            self.markValid()
        except ValueError:
            self.mark_invalid()
            return None
        else:
            return result


@NodeRegistry.register(103)
class TimeDeltaNode(Node):
    """Add or subtract a time offset from a timestamp.

    Inputs:
        - timestamp (float): Base Unix timestamp
        - offset (float): Time offset in seconds (positive = future, negative = past)

    Outputs:
        - result (float): Modified timestamp

    Examples:
        timestamp=1702376400, offset=3600 -> 1702380000 (1 hour later)
        timestamp=1702376400, offset=-86400 -> 1702290000 (1 day earlier)

    """

    op_code = 103
    op_title = "Time Delta"
    content_label = "±"
    content_label_objname = "node_time_delta"

    def __init__(self, scene):
        """Initialize TimeDeltaNode with timestamp and offset inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Add offset to timestamp."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            return None

        timestamp = self.inputs[0].getValue()
        if timestamp is None:
            self.mark_invalid()
            return None

        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            self.mark_invalid()
            return None

        # Get offset value (default to 0 if not connected)
        offset = 0.0
        if self.inputs[1].hasEdges():
            offset_value = self.inputs[1].getValue()
            if offset_value is not None:
                try:
                    offset = float(offset_value)
                except (TypeError, ValueError):
                    self.mark_invalid()
                    return None

        result = timestamp + offset
        self.markValid()
        return result


@NodeRegistry.register(104)
class CompareTimeNode(Node):
    """Compare two timestamps and return the difference.

    Inputs:
        - timestamp1 (float): First Unix timestamp
        - timestamp2 (float): Second Unix timestamp

    Outputs:
        - difference (float): Time difference in seconds (timestamp1 - timestamp2)

    Examples:
        timestamp1=1702380000, timestamp2=1702376400 -> 3600.0 (1 hour difference)
        timestamp1=1702376400, timestamp2=1702380000 -> -3600.0 (negative = earlier)

    """

    op_code = 104
    op_title = "Compare Time"
    content_label = "dt"
    content_label_objname = "node_compare_time"

    def __init__(self, scene):
        """Initialize CompareTimeNode with two timestamp inputs."""
        super().__init__(scene, self.__class__.op_title, inputs=[5, 5], outputs=[5])
        self.value = None

    def init_settings(self):
        """Initialize node settings."""
        super().init_settings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalImplementation(self):
        """Calculate time difference between two timestamps."""
        if not self.inputs[0].hasEdges():
            self.mark_invalid()
            return None

        if not self.inputs[1].hasEdges():
            self.mark_invalid()
            return None

        timestamp1 = self.inputs[0].getValue()
        timestamp2 = self.inputs[1].getValue()

        if timestamp1 is None or timestamp2 is None:
            self.mark_invalid()
            return None

        try:
            timestamp1 = float(timestamp1)
            timestamp2 = float(timestamp2)
        except (TypeError, ValueError):
            self.mark_invalid()
            return None

        result = timestamp1 - timestamp2
        self.markValid()
        return result
