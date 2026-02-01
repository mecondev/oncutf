"""Package: rename_nodes.

Author: Michael Economou
Date: 2026-01-03

oncutf-specific nodes for rename pipeline graph.

Op codes 200+ are reserved for custom application nodes.

Node Types:
    OriginalNameNode (200) - Output original filename
    CounterNode (201) - Sequential numbering
    TextRemovalNode (202) - Remove text patterns
    MetadataNode (203) - Extract EXIF data
    TextInputNode (204) - User-specified text
    TransformNode (205) - Case/trim operations
    ConcatNode (206) - Join multiple strings
    OutputNode (207) - Final filename destination
"""

# TODO: Nodes will be imported here after implementation

__all__: list[str] = [
    # "TextInputNode",
    # "TransformNode",
    # "ConcatNode",
    # "RenameOutputNode",
]
