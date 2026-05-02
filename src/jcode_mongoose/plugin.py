"""
Mongoose ORM edge plugin for jcode.

Detects two patterns in JavaScript/TypeScript files:

1. Model registration — mongoose.model('ModelName', schema)
   → MODEL_DEFINE edge: caller → model node
   Useful for blast radius: change a schema → find all models that use it.

2. Population — query.populate('fieldName')
   → POPULATE edge: caller → the field/model being populated
   Useful for blast radius: rename a model → find every .populate() that
   references it by string.

The model() check requires the receiver to be mongoose, db, or connection
to avoid false positives from unrelated .model() calls (e.g. Backbone).
The populate() check is receiver-agnostic since it's unique enough to Mongoose.
"""
from jcode.domain.models import Edge, Node, NodeId, NodeType
from jcode.storage.object_store import node_id_for

EDGE_MODEL_DEFINE = "model_define"   # model registration site → model node
EDGE_POPULATE     = "populate"       # query caller → populated field/model

# Mongoose instance variable names
_MONGOOSE_OBJECTS = frozenset({"mongoose", "db", "connection", "conn"})


def _text(ts_node, source: bytes) -> str:
    return source[ts_node.start_byte:ts_node.end_byte].decode("utf-8", errors="replace")


def _provisional(name: str, node_type: NodeType = NodeType.FUNCTION) -> Node:
    ph = Node(
        id=NodeId("0" * 64), node_type=node_type,
        name=name, title=name, file_path="<unresolved>",
        line_start=0, line_end=0,
    )
    return Node(
        id=node_id_for(ph), node_type=node_type,
        name=name, title=name, file_path="<unresolved>",
        line_start=0, line_end=0,
    )


def _receiver_name(call_node, source: bytes) -> str:
    """Return the receiver object name for a member_expression call, or ''."""
    func_expr = call_node.children[0] if call_node.children else None
    if func_expr is None or func_expr.type != "member_expression":
        return ""
    obj = func_expr.child_by_field_name("object")
    return _text(obj, source).lower() if obj else ""


def _first_string_arg(call_node, source: bytes) -> str | None:
    """Return the value of the first string/template literal argument, or None."""
    args = next((c for c in call_node.children if c.type == "arguments"), None)
    if args is None:
        return None
    for child in args.children:
        if child.type in ("string", "template_string"):
            return _text(child, source).strip("\"'`")
    return None


class MongoosePlugin:
    """Implements the jcode EdgePlugin protocol for Mongoose."""

    @property
    def handled_names(self) -> frozenset:
        return frozenset({"model", "populate"})

    def handle_call(self, call_node, source: bytes, caller: Node):
        """Dispatch to model or populate handler."""
        func_expr = call_node.children[0] if call_node.children else None
        if func_expr is None:
            return [], []

        if func_expr.type == "member_expression":
            prop = func_expr.child_by_field_name("property")
            method = _text(prop, source) if prop else ""
        else:
            method = _text(func_expr, source)

        if method == "model":
            return self._handle_model(call_node, source, caller)
        if method == "populate":
            return self._handle_populate(call_node, source, caller)
        return [], []

    def _handle_model(self, call_node, source: bytes, caller: Node):
        """
        mongoose.model('User', userSchema)
        → MODEL_DEFINE edge: caller → User (provisional class node)
        """
        if _receiver_name(call_node, source) not in _MONGOOSE_OBJECTS:
            return [], []
        model_name = _first_string_arg(call_node, source)
        if not model_name:
            return [], []
        prov = _provisional(model_name, NodeType.CLASS)
        return [prov], [Edge(
            source_id=caller.id,
            target_id=prov.id,
            edge_type=EDGE_MODEL_DEFINE,
        )]

    def _handle_populate(self, call_node, source: bytes, caller: Node):
        """
        query.populate('posts')
        → POPULATE edge: caller → 'posts' (provisional node)
        """
        field_name = _first_string_arg(call_node, source)
        if not field_name:
            return [], []
        prov = _provisional(field_name)
        return [prov], [Edge(
            source_id=caller.id,
            target_id=prov.id,
            edge_type=EDGE_POPULATE,
        )]


def create() -> MongoosePlugin:
    return MongoosePlugin()
