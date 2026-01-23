"""Node system with registry and base classes.

This module provides the node type registration system and base classes
for creating custom nodes in the node editor.

Classes:
    NodeRegistry: Central registry for node type management.

Built-in Nodes (Core - Op Codes 1-30):
    NumberInputNode, TextInputNode: Input nodes for user data entry.
    OutputNode: Display node for showing results.
    AddNode, SubtractNode, MultiplyNode, DivideNode: Basic math operations.
    EqualNode, NotEqualNode, LessThanNode, etc: Comparison operations.
    IfNode: Conditional switch node.

Extended Nodes (Op Codes 40+):
    String Operations (40-49): Concatenate, Format, Length, Substring, Split.
    Math Extended (50-59): Power, Sqrt, Abs, Min, Max, Round, Modulo.
    Logic Extended (60-69): AND, OR, NOT, XOR.
    Conversion Nodes (70-79): ToString, ToNumber, ToBool, ToInt.
    Utility Nodes (80-89): Constant, Print, Comment, Clamp, Random.
    List Operations (90-99): CreateList, GetItem, ListLength, Append, Join.
    Time/Date Operations (100-109): CurrentTime, FormatDate, ParseDate, TimeDelta, CompareTime.
    Advanced Operations (110-119): RegexMatch, FileRead, FileWrite, HttpRequest.

Usage:
    Create and register a custom node::

        from oncutf.ui.widgets.node_editor.core import Node
        from oncutf.ui.widgets.node_editor.nodes import NodeRegistry

        @NodeRegistry.register(100)
        class MyNode(Node):
            op_code = 100
            op_title = "My Custom Node"

            def __init__(self, scene):
                super().__init__(scene, "My Custom Node")

Author:
    Michael Economou

Date:
    2025-12-11
"""

# Import built-in node types to auto-register them
from oncutf.ui.widgets.node_editor.nodes.advanced_nodes import (
    FileReadNode,
    FileWriteNode,
    HttpRequestNode,
    RegexMatchNode,
)
from oncutf.ui.widgets.node_editor.nodes.conversion_nodes import (
    ToBoolNode,
    ToIntNode,
    ToNumberNode,
    ToStringNode,
)
from oncutf.ui.widgets.node_editor.nodes.input_node import NumberInputNode, TextInputNode
from oncutf.ui.widgets.node_editor.nodes.list_nodes import (
    AppendNode,
    CreateListNode,
    GetItemNode,
    JoinNode,
    ListLengthNode,
)
from oncutf.ui.widgets.node_editor.nodes.logic_nodes import (
    AndNode,
    EqualNode,
    GreaterEqualNode,
    GreaterThanNode,
    IfNode,
    LessEqualNode,
    LessThanNode,
    NotEqualNode,
    NotNode,
    OrNode,
    XorNode,
)
from oncutf.ui.widgets.node_editor.nodes.math_nodes import (
    AbsNode,
    AddNode,
    DivideNode,
    MaxNode,
    MinNode,
    ModuloNode,
    MultiplyNode,
    PowerNode,
    RoundNode,
    SqrtNode,
    SubtractNode,
)
from oncutf.ui.widgets.node_editor.nodes.output_node import OutputNode
from oncutf.ui.widgets.node_editor.nodes.registry import NodeRegistry

# Import extended node types
from oncutf.ui.widgets.node_editor.nodes.string_nodes import (
    ConcatenateNode,
    FormatNode,
    LengthNode,
    SplitNode,
    SubstringNode,
)
from oncutf.ui.widgets.node_editor.nodes.time_nodes import (
    CompareTimeNode,
    CurrentTimeNode,
    FormatDateNode,
    ParseDateNode,
    TimeDeltaNode,
)
from oncutf.ui.widgets.node_editor.nodes.utility_nodes import (
    ClampNode,
    CommentNode,
    ConstantNode,
    PrintNode,
    RandomNode,
)

__all__ = [
    "AbsNode",
    # Math nodes
    "AddNode",
    # Logic extended
    "AndNode",
    "AppendNode",
    "ClampNode",
    "CommentNode",
    "CompareTimeNode",
    # String operations
    "ConcatenateNode",
    # Utility nodes
    "ConstantNode",
    # List operations
    "CreateListNode",
    # Time/Date operations
    "CurrentTimeNode",
    "DivideNode",
    # Logic nodes
    "EqualNode",
    "FileReadNode",
    "FileWriteNode",
    "FormatDateNode",
    "FormatNode",
    "GetItemNode",
    "GreaterEqualNode",
    "GreaterThanNode",
    "HttpRequestNode",
    "IfNode",
    "JoinNode",
    "LengthNode",
    "LessEqualNode",
    "LessThanNode",
    "ListLengthNode",
    "MaxNode",
    "MinNode",
    "ModuloNode",
    "MultiplyNode",
    "NodeRegistry",
    "NotEqualNode",
    "NotNode",
    # Input nodes
    "NumberInputNode",
    "OrNode",
    # Output nodes
    "OutputNode",
    "ParseDateNode",
    # Math extended
    "PowerNode",
    "PrintNode",
    "RandomNode",
    # Advanced operations
    "RegexMatchNode",
    "RoundNode",
    "SplitNode",
    "SqrtNode",
    "SubstringNode",
    "SubtractNode",
    "TextInputNode",
    "TimeDeltaNode",
    "ToBoolNode",
    "ToIntNode",
    "ToNumberNode",
    # Conversion nodes
    "ToStringNode",
    "XorNode",
]
